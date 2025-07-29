from pydantic import BaseModel
from datetime import datetime

# For creating a notification (internal use)
class NotificationCreate(BaseModel):
    user_id: int
    message: str

# For reading/sending to frontend
class NotificationOut(BaseModel):
    id: int
    user_id: int
    message: str
    created_at: datetime
    is_read: bool 

    class Config:
        orm_mode = True


# Pydantic model for request body
class MarkReadRequest(BaseModel):
    notification_id: int
