from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class PlanBase(BaseModel):
    name: str
    description: str
    price_rs: int
    duration_days: int

class PlanCreate(PlanBase):
    pass

class PlanOut(PlanBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class PlanUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    price_rs: Optional[int]
    duration_days: Optional[int]
