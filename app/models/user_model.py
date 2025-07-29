from pydantic import BaseModel, EmailStr
from typing import Literal, Optional
from datetime import datetime

class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: str

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    roles: str
    subscription_status: Optional[str]
    subscription_expiry: Optional[datetime]
    plan_id: Optional[int]
    created_at: datetime

    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    subscription_status: Optional[Literal["active", "inactive", "expired" , "none"]] = None
    plan_id: Optional[int]  = None
    subscription_expiry: Optional[datetime] = None



class SubscriptionInfo(BaseModel):
    plan_name: str
    subscription_start: str
    subscription_expiry: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    subscription_status: str
    subscription: SubscriptionInfo
    class Config:
        orm_mode = True