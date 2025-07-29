from datetime import datetime, timedelta
from fastapi import HTTPException
from app.controllers.user_controller import get_all_users, get_user_details
from app.database.db_connect import test_database_connection

NOTIFICATION_TYPES = [
    {
        "days_before": 0,
        "event": "start",
        "message": "Hello {name}, your {plan} subscription starts today."
    },
    {
        "days_before": 7,
        "event": "reminder",
        "message": "Hello {name}, your {plan} subscription will expire in 7 days."
    },
    {
        "days_before": 3,
        "event": "reminder",
        "message": "Hello {name}, your subscription will expire in 3 days."
    },
    {
        "days_before": 1,
        "event": "final_reminder",
        "message": "Hello {name}, your {plan} subscription will expire tomorrow."
    },
    {
        "days_before": 0,
        "event": "expired",
        "message": "Hello {name}, your {plan} subscription has expired today."
    }
]


# ✅ Used by scheduler daily
def check_and_send_scheduled_notifications():
    users = get_all_users()
    today = datetime.utcnow().date()
    sent_notifications = []

    for user in users:
        name = user["full_name"]
        plan = user.get("plan_name", "subscription")
        user_id = user["id"]

        start_date = parse_date(user["subscription_start"])
        expiry_date = parse_date(user["subscription_expiry"])

        for note in NOTIFICATION_TYPES:
            if note["event"] == "start":
                target_date = start_date
            elif note["event"] == "expired":
                target_date = expiry_date
            else:
                target_date = expiry_date - timedelta(days=note["days_before"])

            if today == target_date:
                message = note["message"].format(name=name, plan=plan)
                if not notification_already_sent(user_id, message):
                    create_notification(user_id, message, note["event"])
                    sent_notifications.append({"user_id": user_id, "event": note["event"], "message": message})

    return {"status": "done", "sent": sent_notifications}


# ✅ Used immediately after payment
def create_start_notification_for_user(user_id: int):
    user = get_user_details(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = datetime.utcnow().date()
    start_date = parse_date(user["subscription_start"])
    if today != start_date:
        return

    name = user["full_name"]
    plan = user.get("plan_name", "subscription")
    message = f"Hello {name}, your {plan} subscription starts today."

    if not notification_already_sent(user_id, message):
        create_notification(user_id, message, "start")


def parse_date(value):
    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d").date()
    return value


def notification_already_sent(user_id: int, message: str):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id FROM notifications
            WHERE user_id = %s AND message = %s AND DATE(created_at) = CURRENT_DATE
        """, (user_id, message))
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()


def create_notification(user_id: int, message: str, event_type: str = None):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO notifications (user_id, message, event_type, is_read)
            VALUES (%s, %s, %s, FALSE)
            RETURNING id
        """, (user_id, message, event_type))
        conn.commit()
        return {"message": "Notification sent", "notification_id": cursor.fetchone()[0]}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()


def delete_notification(notification_id: int):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE notifications
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (notification_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
        conn.commit()
        return {"message": "Notification deleted"}
    finally:
        cursor.close()
        conn.close()


def get_notifications_by_user(user_id: int):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, user_id, message, created_at, is_read
            FROM notifications
            WHERE user_id = %s AND deleted_at IS NULL
            ORDER BY created_at DESC
        """, (user_id,))
        return [
            {
                "id": row[0],
                "user_id": row[1],
                "message": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "is_read": row[4],
            }
            for row in cursor.fetchall()
        ]
    finally:
        cursor.close()
        conn.close()


def count_unread_notifications_by_user(user_id: int) -> int:
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM notifications
            WHERE user_id = %s AND is_read = FALSE AND deleted_at IS NULL
        """, (user_id,))
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()
