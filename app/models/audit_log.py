from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class AuditLogCreate(BaseModel):
    actor_id: Optional[int]  # Nullable if actor deleted
    action: str              # "create", "update", "delete"
    target_table: str        # e.g., "users", "payments"
    target_id: int
    old_data: Optional[Dict] = None
    new_data: Optional[Dict] = None

class AuditLogOut(AuditLogCreate):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
