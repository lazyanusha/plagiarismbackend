from datetime import date, datetime, timedelta, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from app.database.db_connect import test_database_connection
from app.utils.jwt_handler import create_access_token, decode_token, get_current_user, security
from app.controllers import user_controller
from app.models.user_model import UserCreate, UserLogin, UserUpdate
from psycopg2.extras import RealDictCursor


router = APIRouter(prefix="/users", tags=["Users"])


#  Public: Register a user
@router.post("/register")
def register(user: UserCreate):
    conn = test_database_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE email = %s AND deleted_at IS NULL", (user.email,))
    existing_user = cursor.fetchone()
    cursor.close()
    conn.close()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # ✅ Call controller and capture created user
    new_user = user_controller.create_user(user)

    # ✅ Generate token using returned ID
    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={"sub": new_user["email"], "user_id": new_user["id"]},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

#  Public: Login user
@router.post("/login")
def login(user: UserLogin):
    return user_controller.login_user(user)



#  Admin only: Get all users
@router.get("/all")
def get_users(current_user: dict = Depends(get_current_user)) -> Any:
    if current_user["roles"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = user_controller.get_all_users()
    
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": f"{len(users)} user(s) retrieved successfully.",
            "data": users
        }
    )


# Admin only: Get metrics
@router.get("/metrics")
def get_user_metrics(current_user: dict = Depends(get_current_user)):
    if current_user["roles"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    conn = test_database_connection()
    cursor = conn.cursor()

    metrics = {}

    cursor.execute("SELECT COUNT(*) FROM users WHERE deleted_at IS NULL;")
    metrics["total_users"] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(DISTINCT u.id)
        FROM users u
        JOIN payments p ON u.id = p.user_id
        WHERE p.expiry_date > CURRENT_DATE
        AND u.deleted_at IS NULL
        ;
    """)
    metrics["active_subscriptions"] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM users u
        WHERE u.deleted_at IS NULL
        AND NOT EXISTS (
            SELECT 1 FROM payments p 
            WHERE p.user_id = u.id AND p.expiry_date > CURRENT_DATE
        );
    """)
    metrics["expired_subscriptions"] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT pl.name, COUNT(DISTINCT u.id)
        FROM users u
        LEFT JOIN LATERAL (
            SELECT plan_id FROM payments p
            WHERE p.user_id = u.id
            ORDER BY p.expiry_date DESC
            LIMIT 1
        ) latest_payment ON true
        LEFT JOIN plans pl ON latest_payment.plan_id = pl.id
        WHERE u.deleted_at IS NULL
        GROUP BY pl.name;
    """)
    metrics["plan_distribution"] = [{"plan_name": row[0] or "No Plan", "count": row[1]} for row in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) FROM users WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' AND deleted_at IS NULL;")
    metrics["new_users_last_7_days"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE created_at >= CURRENT_DATE - INTERVAL '30 days' AND deleted_at IS NULL;")
    metrics["new_users_last_30_days"] = cursor.fetchone()[0]

    cursor.execute("SELECT roles, COUNT(*) FROM users WHERE deleted_at IS NULL GROUP BY roles;")
    metrics["roles_distribution"] = [{"role": row[0], "count": row[1]} for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return JSONResponse(
        status_code=200,
        content={"success": True, "data": metrics}
    )


# Get user growth data (admin only)
@router.get("/growth")
def get_user_growth(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: dict = Depends(get_current_user)
):
    if current_user["roles"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        conn = test_database_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    DATE(created_at) AS date,
                    COUNT(*) AS count
                FROM users
                WHERE created_at BETWEEN %s AND %s
                GROUP BY DATE(created_at)
                ORDER BY DATE(created_at)
            """, (start_date, end_date))

            rows = cur.fetchall()
            result = [{"date": row[0].isoformat(), "users": row[1]} for row in rows]

        return JSONResponse(
            status_code=200,
            content={"success": True, "data": result}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", tags=["Users"])
def get_logged_in_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("user_id")

    conn = test_database_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, full_name, email, phone, roles, subscription_status
        FROM users
        WHERE id = %s AND deleted_at IS NULL
    """, (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": result[0],
        "full_name": result[1],
        "email": result[2],
        "phone": result[3],
        "roles": result[4],
        "subscription_status": result[5]
    }

#get user details on the basis of userid
@router.get("/{user_id}")
def get_user_route(user_id: int, credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)  
    logged_in_user_id = payload.get("sub")
    logged_in_user_role = payload.get("roles")

    # Allow if admin or if user_id matches logged in user
    if logged_in_user_role != "admin" and logged_in_user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user")

    return user_controller.get_user_details(user_id)


#  Admin or Owner: Update user
@router.patch("/{user_id}")
def update_user_api(
    user_id: int,
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["roles"] == "admin":
        return user_controller.update_user(user_id, user_update)
    
    if current_user["roles"] == "user" and current_user["user_id"] == user_id:
        return user_controller.update_user(user_id, user_update)

    raise HTTPException(status_code=403, detail="Not authorized")



# Admin only: Delete user
@router.delete("/{user_id}")
def delete_user(user_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["roles"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_controller.delete_user(user_id)



#logout route
@router.post("/logout", tags=["Users"])
def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

    conn = test_database_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO blacklisted_tokens (token, expires_at) VALUES (%s, %s)",
        (token, expires_at)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "Logged out successfully"}
