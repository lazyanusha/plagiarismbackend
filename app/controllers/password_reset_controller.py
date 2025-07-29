from datetime import datetime, timedelta
import random
import string
from passlib.context import CryptContext
from fastapi import HTTPException
from app.database.db_connect import test_database_connection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP code."""
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(email: str, otp_code: str):
    """Simulate sending OTP email (replace with actual email sending)."""
    print(f"Sending OTP {otp_code} to email: {email}")

def request_password_reset(email: str):
    """
    Initiates password reset by generating OTP and sending email.
    Returns a success message regardless of email existence for security.
    """
    conn = test_database_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE email = %s AND deleted_at IS NULL", (email,))
        user = cursor.fetchone()

        if not user:
            # Silently succeed to avoid email enumeration
            return {"message": "If the email exists, an OTP has been sent."}

        user_id = user[0]
        otp_code = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        cursor.execute("""
            INSERT INTO password_reset_tokens (user_id, otp_code, expires_at, used)
            VALUES (%s, %s, %s, FALSE)
        """, (user_id, otp_code, expires_at))
        conn.commit()

        send_otp_email(email, otp_code)

        return {"message": "If the email exists, an OTP has been sent."}

    except Exception as e:
        conn.rollback()
        # Consider logging the exception here
        raise HTTPException(status_code=500, detail="Failed to initiate password reset")
    finally:
        cursor.close()
        conn.close()

def confirm_password_reset(email: str, otp_code: str, new_password: str):
    """
    Validates OTP code and resets password if valid.
    """
    conn = test_database_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE email = %s AND deleted_at IS NULL", (email,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid email or code")

        user_id = user[0]

        cursor.execute("""
            SELECT id, expires_at, used FROM password_reset_tokens
            WHERE user_id = %s AND otp_code = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, otp_code))
        token = cursor.fetchone()

        if not token:
            raise HTTPException(status_code=400, detail="Invalid email or code")

        token_id, expires_at, used = token
        now = datetime.utcnow()

        if used:
            raise HTTPException(status_code=400, detail="Code has already been used")

        if expires_at < now:
            raise HTTPException(status_code=400, detail="Code has expired")

        # Optional: Add password complexity validation here

        hashed_password = pwd_context.hash(new_password)

        cursor.execute("""
            UPDATE users SET password = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s
        """, (hashed_password, user_id))

        cursor.execute("""
            UPDATE password_reset_tokens SET used = TRUE WHERE id = %s
        """, (token_id,))

        conn.commit()

        return {"message": "Password reset successful."}

    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        # Consider logging the exception here
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cursor.close()
        conn.close()
