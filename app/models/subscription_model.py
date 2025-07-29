from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PlanInfo(BaseModel):
    id: int
    name: str
    price_rs: float

class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    date: Optional[datetime]
    expiry_date: Optional[datetime]
    deleted_at: Optional[datetime] = None
    status: str 
    plan: PlanInfo
    amount: float
    created_at: Optional[datetime]
