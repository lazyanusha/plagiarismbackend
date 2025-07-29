from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.database.db_connect import test_database_connection
from app.utils.jwt_handler import get_current_user
from app.controllers.notification_controller import (
    check_and_send_scheduled_notifications,
    count_unread_notifications_by_user,
    get_notifications_by_user,
    create_start_notification_for_user,
)
from app.models.notification_model import MarkReadRequest, NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=List[NotificationOut])
def get_user_notifications(current_user: dict = Depends(get_current_user)):
    check_and_send_scheduled_notifications()
    return get_notifications_by_user(current_user["user_id"])


@router.get("/unread_count")
def get_unread_notifications_count(current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    count = count_unread_notifications_by_user(current_user["user_id"])
    return {"unread_count": count}


@router.post("/mark_read")
def mark_as_read(payload: MarkReadRequest, current_user: dict = Depends(get_current_user)):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE notifications
            SET is_read = TRUE
            WHERE id = %s AND user_id = %s
        """, (payload.notification_id, current_user["user_id"]))
        conn.commit()
        return {"message": "Marked as read"}
    finally:
        cursor.close()
        conn.close()


@router.post("/start-notification/{user_id}")
def send_start_notification_for_user(user_id: int, current_user: dict = Depends(get_current_user)):
    # optional: limit this to admin or self
    create_start_notification_for_user(user_id)
    return {"message": "Start notification checked"}
