from fastapi import APIRouter, HTTPException
from app.models.password_reset_model import PasswordResetConfirm, PasswordResetRequest
from app.controllers.password_reset_controller import request_password_reset, confirm_password_reset

router = APIRouter(prefix="/password-reset", tags=["Password Reset"])

@router.post("/request")
def password_reset_request_endpoint(data: PasswordResetRequest):
    try:
        request_password_reset(data.email)
    except Exception:
        # Always return success to avoid email enumeration
        pass
    return {"message": "If the email exists, a reset code has been sent."}

@router.post("/confirm")
def password_reset_confirm_endpoint(data: PasswordResetConfirm):
    confirm_password_reset(data.email, data.otp_code, data.new_password)
    return {"message": "Password reset successfully"}
