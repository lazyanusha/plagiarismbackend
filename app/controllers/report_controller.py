# app/controllers/report_controller.py

from fastapi import HTTPException
from app.database.db_connect import test_database_connection
from datetime import datetime, timedelta

def create_report(report_data: dict, user_id: int):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO reports (
                user_id, submitted_document, unique_score, total_exact_score, 
                total_partial_score, words, characters, citation_status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            user_id,
            report_data.get('submitted_document'),
            report_data.get('unique_score'),
            report_data.get('total_exact_score'),
            report_data.get('total_partial_score'),
            report_data.get('words', 0),
            report_data.get('characters', 0),
            report_data.get('citation_status')
        ))
        report_id = cursor.fetchone()[0]
        conn.commit()
        return {"message": "Report created successfully.", "report_id": report_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


def fetch_reports_history(user_id: int, page: int = 1, limit: int = 10):
    offset = (page - 1) * limit
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, user_id, submitted_document, total_exact_score, total_partial_score, 
                   unique_score, words, characters, citation_status, created_at
            FROM reports
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (user_id, limit, offset))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]

        cursor.execute("SELECT COUNT(*) FROM reports WHERE user_id = %s", (user_id,))
        total_count = cursor.fetchone()[0]

        return {
            "reports": results,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


def get_report_by_id(report_id: int, user_id: int, force: bool = False):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        print(f"🔍 Fetching report {report_id} for user {user_id}")
        cursor.execute("SELECT user_id FROM reports WHERE id = %s", (report_id,))
        owner_row = cursor.fetchone()
        if not owner_row:
            raise HTTPException(status_code=404, detail="Report not found")

        report_owner_id = owner_row[0]
        print(f"Report owner ID: {report_owner_id} (type {type(report_owner_id)})")
        print(f"Provided user_id: {user_id} (type {type(user_id)})")

        if not force and report_owner_id != user_id:
            print(f"Access denied: user_id {user_id} does not match owner_id {report_owner_id}")
            raise HTTPException(status_code=403, detail="Unauthorized to access this report")

        cursor.execute("SELECT * FROM reports WHERE id = %s", (report_id,))
        row = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


def delete_report(report_id: int, user_id: int = None, force: bool = False):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM reports WHERE id = %s", (report_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Report not found")

        report_owner_id = row[0]

        if user_id is not None and isinstance(user_id, str):
            user_id = int(user_id)

        if not force and user_id != report_owner_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this report")

        cursor.execute("DELETE FROM reports WHERE id = %s", (report_id,))
        conn.commit()
        return {"message": "Report deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def fetch_all_reports_admin(page: int = 1, limit: int = 10):
    offset = (page - 1) * limit
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
           SELECT reports.id, 
                  reports.submitted_document, 
                  reports.total_exact_score, 
                  reports.total_partial_score,
                  reports.unique_score, 
                  reports.citation_status, 
                  reports.created_at,
                  users.full_name
            FROM reports
            JOIN users ON reports.user_id = users.id
            ORDER BY reports.id ASC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        reports = [dict(zip(columns, row)) for row in rows]

        cursor.execute("SELECT COUNT(*) FROM reports")
        total_count = cursor.fetchone()[0]

        return {
            "reports": reports,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()
