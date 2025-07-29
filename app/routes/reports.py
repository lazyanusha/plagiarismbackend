# app/routers/report_router.py

import datetime
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from app.controllers.report_controller import (
    create_report,
    delete_report,
    get_report_by_id,
    fetch_reports_history,
    fetch_all_reports_admin,
)
from app.database.db_connect import test_database_connection
from app.utils.jwt_handler import get_current_user
from app.utils.role_handle import require_admin

router = APIRouter(prefix="/reports", tags=["reports"])

@router.post("/", status_code=201)
def save_report(
    report: dict,
    current_user: dict = Depends(get_current_user)
):
    try:
        result = create_report(report, current_user["user_id"])
        return {
            "message": "Plagiarism report saved successfully.",
            "report_id": result["report_id"]
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {str(e)}")


@router.get("/user/{report_id}")
def get_single_user_report(
    report_id: int,
    current_user: dict = Depends(get_current_user)
):
    return get_report_by_id(report_id, user_id=int(current_user["user_id"]), force=False)


@router.delete("/user/{report_id}")
def delete_user_report(
    report_id: int,
    current_user: dict = Depends(get_current_user)
):
    return delete_report(report_id, user_id=current_user["user_id"], force=False)


@router.get("/history", response_model=dict)
def get_reports_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    current_user: dict = Depends(get_current_user)
):
    return fetch_reports_history(current_user["user_id"], page, limit)


@router.get("/all")
def admin_get_all_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=100),
    current_user: dict = Depends(require_admin)
):
    return fetch_all_reports_admin(page, limit)


@router.get("/usage")
def get_report_usage(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    period: str = Query("month", regex="^(day|week|month|year)$")
):
    if end_date is None:
        end_date = datetime.utcnow()
    if start_date is None:
        start_date = end_date - timedelta(days=180)

    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                date_trunc(%s, created_at) AS period,
                COUNT(*) AS report_count
            FROM reports
            WHERE created_at BETWEEN %s AND %s
            GROUP BY period
            ORDER BY period ASC;
        """, (period, start_date, end_date))

        rows = cursor.fetchall()
        results = [{"period": row[0].isoformat(), "count": row[1]} for row in rows]

        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()
        conn.close()
