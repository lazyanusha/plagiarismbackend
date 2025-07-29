from app.database.db_connect import test_database_connection
from fastapi import HTTPException

def create_audit_log(log):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO audit_logs (
                actor_id, action, target_table, target_id,
                old_data, new_data
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            log.actor_id,
            log.action,
            log.target_table,
            log.target_id,
            log.old_data,
            log.new_data
        ))
        conn.commit()
        return {"message": "Audit log recorded"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

def get_all_audit_logs():
    conn = test_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY created_at DESC")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in rows]
