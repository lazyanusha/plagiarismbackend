from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.utils.jwt_handler import create_access_token, decode_token, security
from app.database.db_connect import test_database_connection

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/refresh")
def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # ✅ Fetch the user's role from the database
        conn = test_database_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT roles FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        roles = row[0]  # assuming roles is a string like 'admin'

        # ✅ Include roles in the new access token
        new_token = create_access_token({"user_id": user_id, "roles": roles})
        return {"access_token": new_token}
    except Exception as e:
        print("Refresh token error:", e)
        raise HTTPException(status_code=401, detail="Could not refresh token")
