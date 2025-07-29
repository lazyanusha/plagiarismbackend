from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional

# Used when initiating a payment
class PaymentRequest(BaseModel):
    plan_name: str
    amount: int
    user_id: int
    plan_id: int
    full_name: str
    email: str
    phone: Optional[str] = None

# Used when sending payment verification info back to frontend
class PaymentVerificationResponse(BaseModel):
    status: str
    amount: float
    user_id: int
    plan_id: int
    payment_id: int

# Used for internal DB operations
class PaymentCreate(BaseModel):
    user_id: int
    plan_id: int
    amount: float
    date: date  # Use `date` if time is not needed

# Optional update model (not used yet, reserved for future features)
class PaymentUpdate(BaseModel):
    plan_id: Optional[int] = None
    amount: Optional[float] = None
    date: Optional[date] = None # type: ignore

# Verification request sent to server
class PaymentVerificationRequest(BaseModel):
    pidx: str
    transaction_id: Optional[str] = None

# Plan returned in nested output
class PlanOut(BaseModel):
    id: int
    name: str
    price_rs: float

    class Config:
        orm_mode = True


# Output for a basic payment record with flattened fields
class PaymentOut(BaseModel):
    id: int
    user_id: int
    plan_id: int
    plan_name:str
    amount: float
    date: date
    expiry_date: datetime
    full_name: str
    email: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    class Config:
        orm_mode = True



