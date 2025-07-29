from fastapi import Depends, HTTPException
from app.utils.jwt_handler import get_current_user

def require_admin(current_user: dict = Depends(get_current_user)):
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
