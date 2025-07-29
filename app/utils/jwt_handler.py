from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv
from jose import jwt, JWTError , ExpiredSignatureError

from app.database.db_connect import test_database_connection
load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "secret")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "sub": str(int(data.get("user_id")))})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "sub": str(int(data.get("user_id")))})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


# Decode and verify
def decode_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        print("Decoded JWT payload:", payload) 
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# FastAPI dependency to get current user
def is_token_blacklisted(token: str):
    conn = test_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM blacklisted_tokens WHERE token = %s", (token,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None


def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    if is_token_blacklisted(token.credentials):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    payload = decode_token(token.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return {"user_id": int(user_id), **payload}
