from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.database.db_connect import test_database_connection
from app.models.subscription_model import SubscriptionResponse
from app.routes.users import get_current_user

router = APIRouter()

@router.get("/subscriptions/user", response_model=List[SubscriptionResponse], status_code=200)
def get_payments_by_user_id(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]

    try:
        conn = test_database_connection()
        cursor = conn.cursor()
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
                p.deleted_at,
                p.created_at,
                u.full_name,
                u.email
            FROM payments p
            JOIN plans pl ON pl.id = p.plan_id
            JOIN users u ON u.id = p.user_id
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
