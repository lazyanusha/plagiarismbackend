from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List, Optional

from app.routes.users import get_current_user
from app.models.payment_model import (
    PaymentRequest,
    PaymentVerificationRequest,
    PaymentVerificationResponse,
    PaymentOut,
)
from app.controllers.payment_controller import (
    cancel_payment_by_id,
    confirm_khalti_payment,
    get_payment_by_id,
    get_payments_for_user,
    initiate_khalti_payment,
    get_all_payments,
    soft_delete_payment,
)

router = APIRouter()

@router.post("/payments/initiate", response_model=dict, status_code=status.HTTP_201_CREATED)
def initiate_payment_endpoint(
    payment_data: PaymentRequest,
    current_user: dict = Depends(get_current_user),
):
    print(f"Initiate payment request received: {payment_data}")
    if not payment_data:
        raise HTTPException(status_code=400, detail="Payment request data is empty")

    if payment_data.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="User ID mismatch")

    try:
        payment_url = initiate_khalti_payment(payment_data)
        print(f"Payment URL generated: {payment_url}")
        return {"payment_url": payment_url}
    except HTTPException as e:
        print(f"Error during payment initiation: {e.detail}")
        raise e
    

@router.post("/payments/verify", response_model=PaymentVerificationResponse)
def verify_payment(
    payment_request: PaymentVerificationRequest,
    current_user: dict = Depends(get_current_user),
):
    pidx = payment_request.pidx
    transaction_id = payment_request.transaction_id

    payment_info = confirm_khalti_payment(pidx, current_user["user_id"])

    if not payment_info:
        raise HTTPException(status_code=400, detail="Payment verification failed.")

    return payment_info



@router.get("/payments/all", response_model=List[PaymentOut], status_code=status.HTTP_200_OK)
def read_all_payments(current_user: dict = Depends(get_current_user)):
    print(f"User {current_user['user_id']} ({current_user['roles']}) requested all payments")
    if current_user["roles"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    payments = get_all_payments()
    print(f"Returning {len(payments)} payments")
    return payments


@router.get("/payments/user", response_model=List[PaymentOut], status_code=200)
def get_payments_by_user_id(current_user: dict = Depends(get_current_user)):
    if current_user["roles"] != "admin":
        user_id = current_user["user_id"]
    else:
      
        user_id = current_user["user_id"]  
    
    payments = get_payments_for_user(user_id)
    return payments


@router.put("/payments/cancel/{payment_id}", response_model=PaymentOut, status_code=200)
def cancel_payment(
    payment_id: int,
    current_user: dict = Depends(get_current_user),
):
    # Include cancelled payments to properly check if already cancelled
    payment = get_payment_by_id(payment_id, include_cancelled=True)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if "admin" in current_user.get("roles", []):
        # Admin can cancel any payment
        pass
    elif str(payment["user_id"]) == str(current_user["user_id"]):
        # Owner can cancel their own payment
        pass
    else:
        raise HTTPException(status_code=403, detail="Not authorized")

    if payment["deleted_at"] is not None:
        raise HTTPException(status_code=400, detail="Already cancelled")

    updated_payment = cancel_payment_by_id(payment_id)
    return updated_payment


def delete_payment(
    payment_id: int,
    current_user: dict = Depends(get_current_user),
):
    payment = get_payment_by_id(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if "admin" in current_user.get("roles", []):
        pass
    elif payment.user_id == current_user["user_id"]:
        pass
    else:
        raise HTTPException(status_code=403, detail="Not authorized")

    soft_delete_payment(payment_id)
    return
