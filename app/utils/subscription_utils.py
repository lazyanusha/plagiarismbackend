from datetime import datetime, timedelta
from app.database.db_connect import test_database_connection

def check_subscriptions():
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)

        # 1. Expire subscriptions
        cursor.execute("""
            UPDATE users
            SET subscription_status = 'inactive'
            WHERE subscription_expiry IS NOT NULL
              AND subscription_expiry < %s
              AND subscription_status = 'active'
        """, (now,))

        # 2. Send notification for users expiring tomorrow
        cursor.execute("""
            SELECT id, full_name, subscription_expiry FROM users
            WHERE subscription_expiry::date = %s::date
              AND subscription_status = 'active'
        """, (tomorrow.date(),))
        users_expiring = cursor.fetchall()

        for user in users_expiring:
            user_id, name, expiry = user
            message = f"Dear {name}, your subscription will expire on {expiry.date()}. Please renew to continue using all features."

            # Avoid duplicate notifications
            cursor.execute("""
                SELECT 1 FROM notifications
                WHERE user_id = %s AND message = %s
            """, (user_id, message))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO notifications (user_id, message)
                    VALUES (%s, %s)
                """, (user_id, message))

        conn.commit()
        print("✅ Subscription status and notifications checked.")
    except Exception as e:
        conn.rollback()
        print("❌ Error during subscription check:", e)
    finally:
        cursor.close()
        conn.close()
