from datetime import datetime, timedelta
import psycopg2 # type: ignore
from passlib.hash import bcrypt # type: ignore
from app.utils.jwt_handler import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, create_access_token, create_refresh_token
from app.models.user_model import UserCreate, UserLogin, UserUpdate
from app.database.db_connect import test_database_connection
from fastapi import HTTPException
from passlib.context import CryptContext

def create_user(user: UserCreate):
    conn = test_database_connection()
    cursor = conn.cursor()

    hashed_password = bcrypt.hash(user.password)
    try:
        cursor.execute("""
            INSERT INTO users (full_name, email, phone, password, roles)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, full_name, email, phone, roles, created_at;
        """, (user.full_name, user.email, user.phone, hashed_password, 'user'))

        result = cursor.fetchone()
        conn.commit()
        return {
            "id": result[0],
            "full_name": result[1],
            "email": result[2],
            "phone": result[3],
            "roles": result[4],
            "created_at": result[5]
        }

    except psycopg2.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Email or phone already registered.")
    finally:
        cursor.close()
        conn.close()


def login_user(user: UserLogin):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, full_name, email, phone, password, roles FROM users WHERE email = %s", (user.email,))
        result = cursor.fetchone()

        if not result or not bcrypt.verify(user.password, result[4]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        user_id = result[0]

        # Set custom expiration if remember_me is True
        if user.remember_me:
            access_exp = timedelta(days=7)
            refresh_exp = timedelta(days=30)
        else:
            access_exp = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            refresh_exp = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        access_token = create_access_token({"user_id": user_id, "roles": result[5]}, expires_delta=access_exp)
        refresh_token = create_refresh_token({"user_id": user_id, "roles": result[5]}, expires_delta=refresh_exp)

        return {
            "id": result[0],
            "full_name": result[1],
            "email": result[2],
            "phone": result[3],
            "roles": result[5],
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    finally:
        cursor.close()
        conn.close()


def get_all_users():
    conn = test_database_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            u.id, u.full_name, u.email, u.phone,
            p.date AS subscription_start,
            p.expiry_date AS subscription_expiry,
            pl.name AS plan_name,
            CASE 
                WHEN p.expiry_date > NOW() THEN 'active'
                ELSE 'inactive'
            END AS subscription_status
        FROM users u
        LEFT JOIN (
            SELECT DISTINCT ON (user_id) *
            FROM payments
            ORDER BY user_id, expiry_date DESC
        ) p ON u.id = p.user_id
        LEFT JOIN plans pl ON p.plan_id = pl.id
        WHERE u.deleted_at IS NULL AND u.roles <> 'admin';
    """)

    users = cursor.fetchall()
    result = []

    for u in users:
        subscription_start = u[4]
        subscription_expiry = u[5]
        result.append({
            "id": u[0],
            "full_name": u[1],
            "email": u[2],
            "phone": u[3],
            "subscription_start": subscription_start.isoformat() if subscription_start else None,
            "subscription_expiry": subscription_expiry.isoformat() if subscription_expiry else None,
            "plan_name": u[6],
            "subscription_status": u[7]
        })

    cursor.close()
    conn.close()
    return result


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def update_user(user_id: int, user_update: UserUpdate):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        data = user_update.dict(exclude_unset=True)

        if not data:
            raise HTTPException(status_code=400, detail="No data provided for update")

        # Hash password if it's part of the update
        if "password" in data:
            data["password"] = pwd_context.hash(data["password"])

        # Build SQL update statement
        set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
        values = list(data.values()) + [user_id]

        sql = f"""
            UPDATE users
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, full_name, email, phone, subscription_status, plan_id, updated_at;
        """
        cursor.execute(sql, values)
        updated_user = cursor.fetchone()
        conn.commit()

        if updated_user:
            keys = [desc[0] for desc in cursor.description]
            return dict(zip(keys, updated_user))

        raise HTTPException(status_code=404, detail="User not found")
    finally:
        cursor.close()
        conn.close()


def delete_user(user_id: int):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s RETURNING id;", (user_id,))
        result = cursor.fetchone()
        conn.commit()
        if result:
            return {"message": "User deleted (soft) successfully"}
        raise HTTPException(status_code=404, detail="User not found")
    finally:
        cursor.close()
        conn.close()


def get_user_details(user_id: int) -> dict:
    try:
        conn = test_database_connection()
        cursor = conn.cursor()

        # Basic user info
        cursor.execute("""
            SELECT id, full_name, email, phone, roles, deleted_at
            FROM users
            WHERE id = %s AND deleted_at IS NULL
        """, (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        user = {
            "id": row[0],
            "full_name": row[1],
            "email": row[2],
            "phone": row[3],
            "roles": row[4],
        }

        now = datetime.utcnow().date()

        # Fetch subscriptions
        cursor.execute("""
    SELECT
        pl.name AS plan_name,
        p.date AS payment_date,
        pl.duration_days
    FROM payments p
    JOIN plans pl ON pl.id = p.plan_id
    WHERE p.user_id = %s 
    ORDER BY p.date ASC
""", (user_id,))

        sub_rows = cursor.fetchall()
        subscriptions = []

        # stacking logic
        current_start = None
        now = datetime.utcnow().date()

        for plan_name, payment_date, duration in sub_rows:
            # Ensure datetime
            if isinstance(payment_date, str):
                payment_date = datetime.fromisoformat(payment_date).date()
            elif isinstance(payment_date, datetime):
                payment_date = payment_date.date()

            if current_start and payment_date < current_start:
                # Stack the plan on the end of previous
                start = current_start
            else:
                start = payment_date

            expiry = start + timedelta(days=duration)
            current_start = expiry  # update for next plan

            if start <= now <= expiry:
                status = "currently active"
            elif now < start:
                status = "upcoming"
            else:
                status = "expired"

            subscriptions.append({
                "plan_name": plan_name,
                "start_date": start.isoformat(),
                "expiry_date": expiry.isoformat(),
                "status": status
            })

        user["subscriptions"] = subscriptions
        user["subscription_status"] = (
            "active" if any(sub["status"] == "currently active" for sub in subscriptions)
            else "expired"
        )

        return user

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user: {str(e)}")
    finally:
        cursor.close()
        conn.close()



