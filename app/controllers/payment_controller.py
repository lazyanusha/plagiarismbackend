import os
import requests
from datetime import datetime, timedelta
from fastapi import HTTPException
from app.controllers.notification_controller import create_notification, notification_already_sent
from app.models.payment_model import PaymentRequest
from app.database.db_connect import test_database_connection

# Khalti endpoints and secret key
KHALTI_INITIATE_URL = "https://a.khalti.com/api/v2/epayment/initiate/"
KHALTI_LOOKUP_URL = "https://a.khalti.com/api/v2/epayment/lookup/"
KHALTI_SECRET_KEY = f"Key {os.getenv("KHALTI_SECRET_KEY")}"
# 1. Initiate Khalti Payment
def initiate_khalti_payment(data: PaymentRequest) -> str:
    if not data:
        raise HTTPException(status_code=400, detail="Payment request data is empty")

    if not all([data.user_id, data.plan_name, data.amount, data.plan_id]):
        raise HTTPException(status_code=400, detail="Missing payment request data")

    payload = {
        "return_url": "http://localhost:5173/payment-status",  # after successful/failed payment
        "website_url": "http://localhost:5173/",
        "amount": data.amount,
        "purchase_order_id": f"order_{data.user_id}_{data.plan_name}_{datetime.utcnow().timestamp()}",
        "purchase_order_name": data.plan_name,
        "product_identity": str(data.plan_id),  # required for lookup
        "customer_info": {
            "name": data.full_name,
            "email": data.email,
            "phone": data.phone,
        }
    }
    headers = {
        "Authorization": KHALTI_SECRET_KEY,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(KHALTI_INITIATE_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

        payment_url = result.get("payment_url")
        pidx = result.get("pidx") 

        if not payment_url or not pidx:
            raise HTTPException(status_code=500, detail=f"No payment URL or pidx returned. Response: {result}")


        conn = test_database_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO khalti_payments (pidx, user_id, plan_id, amount, status, created_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (pidx, data.user_id, data.plan_id, data.amount, 'initiated')
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save payment initiation: {str(e)}")
        finally:
            cursor.close()
            conn.close()

        return payment_url

    except requests.HTTPError as http_err:
        try:
            error_detail = response.json()
        except Exception:
            error_detail = response.text
        raise HTTPException(status_code=502, detail=f"Khalti error: {http_err}. Response: {error_detail}")
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Khalti request failed: {str(e)}")


# 2. Confirm Khalti Payment
def confirm_khalti_payment(pidx: str, user_id: int):
    conn = test_database_connection()
    cursor = conn.cursor()

    try:
        # 1. Fetch payment initiation record from khalti_payments
        cursor.execute(
            "SELECT plan_id, user_id, amount, status FROM khalti_payments WHERE pidx = %s",
            (pidx,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="Payment initiation record not found")

        plan_id_db, user_id_db, amount_db, status_db = row

        if user_id != user_id_db:
            print(f"Incoming user_id: {user_id}, DB user_id: {user_id_db}")

            raise HTTPException(status_code=403, detail="User ID mismatch")

        # 2. Fetch plan duration_days
        cursor.execute("SELECT name, duration_days FROM plans WHERE id = %s", (plan_id_db,))
        plan_row = cursor.fetchone()
        if not plan_row:
            raise HTTPException(status_code=400, detail="Plan not found")
        plan_name, duration_days = plan_row


        # 3. Verify payment with Khalti lookup API
        headers = {
            "Authorization": KHALTI_SECRET_KEY,
            "Content-Type": "application/json",
        }
        payload = {"pidx": pidx}
        response = requests.post(KHALTI_LOOKUP_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        status = data.get("status")
        if status != "Completed":
            raise HTTPException(status_code=400, detail=f"Payment status is not completed: {status}")

        # 4. Check if payment already recorded
        cursor.execute("SELECT id, expiry_date FROM payments WHERE khalti_token = %s", (pidx,))
        existing_payment = cursor.fetchone()
        if existing_payment:
            payment_id, existing_expiry = existing_payment
            return {
                "status": "Confirmed",
                "amount": amount_db,
                "user_id": user_id,
                "plan_id": plan_id_db,
                "payment_id": payment_id,
                "subscription_expiry": existing_expiry.isoformat() if existing_expiry else None,
            }

        dates = calculate_subscription_dates(user_id, duration_days)
        start_date = datetime.fromisoformat(dates["start_date"]).date()
        new_expiry = datetime.fromisoformat(dates["expiry_date"]).date()


        # 6. Insert new payment with expiry_date
        cursor.execute(
            """
            INSERT INTO payments (user_id, plan_id, amount, date, expiry_date, created_at, khalti_token)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
            RETURNING id, created_at
            """,
            (user_id, plan_id_db, amount_db, start_date, new_expiry, pidx),
        )
        payment_id, created_at = cursor.fetchone()

        # 7. Update user's subscription_status based on active payments
        cursor.execute("""
            SELECT plan_id FROM payments
            WHERE user_id = %s AND expiry_date > NOW() AND deleted_at IS NULL
            ORDER BY expiry_date DESC
            LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()

        if row:
            new_status = 'active'
            latest_plan_id = row[0]
        else:
            new_status = 'inactive'
            latest_plan_id = None  

        # Update users table with subscription_status and plan_id
        cursor.execute("""
            UPDATE users SET subscription_status = %s, plan_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s
        """, (new_status, latest_plan_id, user_id))


        # 8. Update khalti_payments status to 'completed'
        cursor.execute(
            "UPDATE khalti_payments SET status = 'completed' WHERE pidx = %s",
            (pidx,)
        )

        # Fetch user's name for notification
        cursor.execute("SELECT full_name FROM users WHERE id = %s", (user_id,))
        user_row = cursor.fetchone()
        user_name = user_row[0] if user_row else "User"

        # Format start notification message
        start_message = f"Hello {user_name}, your {plan_name} subscription starts today."

        # Avoid duplicate and send notification
        if not notification_already_sent(user_id, start_message):
            create_notification(
                user_id=user_id,
                message=start_message,
                event_type="start"
            )

        conn.commit()


    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Payment confirmation failed: {str(e)}")
    finally:
        cursor.close()
        conn.close()

    return {
        "status": status,
        "amount": amount_db,
        "user_id": user_id,
        "plan_id": plan_id_db,
        "payment_id": payment_id,
        "created_at": created_at,
        "subscription_expiry": new_expiry.isoformat(),
    }

# 3. Admin: Fetch all payments
def get_all_payments() -> list[dict]:
    try:
        conn = test_database_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.user_id, u.full_name, u.email, p.plan_id, pl.name AS plan_name, 
           p.amount, p.date, p.expiry_date, p.created_at
            FROM payments p
            JOIN users u ON u.id = p.user_id
            JOIN plans pl ON pl.id = p.plan_id
            ORDER BY p.created_at DESC
        """)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch payments: {str(e)}")
    finally:
        cursor.close()
        conn.close()


def get_payments_for_user(user_id: int):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT 
                p.id,
                p.user_id,
                p.plan_id,
                pl.name AS plan_name,
                pl.price_rs,
                p.amount,
                p.date AS start_date,
                p.expiry_date,
                p.deleted_at,   -- add this
                p.created_at
            FROM payments p
            JOIN plans pl ON pl.id = p.plan_id
            WHERE p.user_id = %s
            ORDER BY p.expiry_date DESC
            """,
            (user_id,)
    )

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        payments = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            payments.append({
                "id": row_dict["id"],
                "user_id": row_dict["user_id"],
                "date": row_dict["start_date"].isoformat() if row_dict["start_date"] else None,
                "expiry_date": row_dict["expiry_date"].isoformat() if row_dict["expiry_date"] else None,
                "deleted_at": row_dict["deleted_at"].isoformat() if row_dict["deleted_at"] else None,  
                "status": "cancelled" if row_dict["deleted_at"] else "active",
                "plan": {
                    "id": row_dict["plan_id"],
                    "name": row_dict["plan_name"],
                    "price_rs": row_dict["price_rs"],
                },
                "amount": row_dict["amount"],
                "created_at": row_dict["created_at"].isoformat() if row_dict["created_at"] else None,
            })

        return payments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch payments: {str(e)}")
    finally:
        cursor.close()
        conn.close()



def soft_delete_payment(payment_id: int):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM payments WHERE id = %s AND deleted_at IS NULL",
            (payment_id,)
        )
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Payment not found or already deleted")

        cursor.execute(
            """
            UPDATE payments
            SET deleted_at = %s, updated_at = %s
            WHERE id = %s
            """,
            (datetime.utcnow(), datetime.utcnow(), payment_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete payment: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def cancel_payment_by_id(payment_id: int):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        now = datetime.utcnow()
        cursor.execute(
            "UPDATE payments SET deleted_at = %s WHERE id = %s RETURNING *",
            (now, payment_id)
        )
        updated = cursor.fetchone()
        if not updated:
            return None
        columns = [desc[0] for desc in cursor.description]
        payment_dict = dict(zip(columns, updated))

        # Add plan info
        cursor.execute("SELECT id, name FROM plans WHERE id = %s", (payment_dict["plan_id"],))
        plan_row = cursor.fetchone()
        if plan_row:
            plan_columns = [desc[0] for desc in cursor.description]
            plan_data = dict(zip(plan_columns, plan_row))
            payment_dict["plan"] = plan_data
            # Add flat plan_name field if required by Pydantic model
            payment_dict["plan_name"] = plan_data["name"]
        else:
            payment_dict["plan"] = None
            payment_dict["plan_name"] = None

        # Add user info (full_name and email)
        cursor.execute("SELECT full_name, email FROM users WHERE id = %s", (payment_dict["user_id"],))
        user_row = cursor.fetchone()
        if user_row:
            user_columns = [desc[0] for desc in cursor.description]
            user_data = dict(zip(user_columns, user_row))
            payment_dict.update(user_data)
        else:
            payment_dict["full_name"] = None
            payment_dict["email"] = None

        conn.commit()
        return payment_dict
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cancel payment: {str(e)}")
    finally:
        cursor.close()
        conn.close()


def get_payment_by_id(payment_id: int, include_cancelled=False):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        query = "SELECT * FROM payments WHERE id = %s"
        params = [payment_id]
        if not include_cancelled:
            query += " AND deleted_at IS NULL"
        cursor.execute(query, params)
        payment = cursor.fetchone()
        if not payment:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, payment))
    finally:
        cursor.close()
        conn.close()



def calculate_subscription_dates(user_id: int, plan_duration_days: int):
    """
    Returns appropriate start and expiry dates for a new subscription.
    If a valid existing subscription exists, stack after expiry.
    Else, start from today.
    """
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        now = datetime.utcnow().date()

        # Fetch latest active (not deleted) and non-expired subscription expiry date
        cursor.execute("""
            SELECT MAX(expiry_date)
            FROM payments
            WHERE user_id = %s AND deleted_at IS NULL
        """, (user_id,))
        row = cursor.fetchone()
        latest_expiry = row[0] if row else None

        # Start after expiry if still active, else today
        if latest_expiry is not None and latest_expiry > now:
            start_date = latest_expiry
        else:
            start_date = now


        expiry_date = start_date + timedelta(days=plan_duration_days)

        return {
            "start_date": start_date.isoformat(),
            "expiry_date": expiry_date.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to determine subscription dates: {str(e)}")
    finally:
        cursor.close()
        conn.close()
