from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.utils.role_handle import require_admin
from app.utils.jwt_handler import get_current_user
from app.database.db_connect import test_database_connection

router = APIRouter(prefix="/financial", tags=["Financial"])

@router.get("/metrics")
def get_payment_metrics(_: dict = Depends(require_admin)):
   
    conn = test_database_connection()
    cursor = conn.cursor()

    # Total revenue: sum of all payments (assuming all are completed)
    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM payments;")
    total_revenue = float(cursor.fetchone()[0])

    # Total payments count (consider all payments)
    cursor.execute("SELECT COUNT(*) FROM payments;")
    payments_completed = cursor.fetchone()[0]

    # We don't have status, so failed payments = 0 or skip
    cursor.execute("SELECT COUNT(*) FROM payments WHERE deleted_at IS NOT NULL;")
    payments_failed = cursor.fetchone()[0]

    # ARPU = total revenue / total payments
    arpu = total_revenue / payments_completed if payments_completed else 0

    # Revenue by plan
    cursor.execute("""
        SELECT 
            pl.name, 
            COALESCE(SUM(p.amount), 0) AS total_amount
        FROM payments p
        LEFT JOIN plans pl ON p.plan_id = pl.id 
        GROUP BY pl.name;
    """)
    revenue_by_plan = [
        {"name": row[0] or "Unknown", "revenue": float(row[1])}
        for row in cursor.fetchall()
    ]

    cursor.close()
    conn.close()

    return {
        "total_revenue": total_revenue/100,
        "payments_completed": payments_completed,
        "payments_failed": payments_failed,
        "arpu": arpu/100,
        "revenue_by_plan": revenue_by_plan,
    }



@router.get("/metrics/usage")
def get_usage_metrics(_: dict = Depends(require_admin)):

    conn = test_database_connection()
    cursor = conn.cursor()

    # Total reports uploaded
    cursor.execute("SELECT COUNT(*) FROM reports WHERE deleted_at IS NULL;")
    total_reports = cursor.fetchone()[0]

    # Average usage per user
    cursor.execute("""
        SELECT
          (SELECT COUNT(*) FROM reports WHERE deleted_at IS NULL)::FLOAT /
          NULLIF((SELECT COUNT(DISTINCT user_id) FROM reports WHERE deleted_at IS NULL), 0)
    """)
    avg_usage_per_user = cursor.fetchone()[0] or 0

    # Usage over time for last 30 days
    cursor.execute("""
        SELECT
          DATE(created_at) AS date,
          COUNT(*) AS count
        FROM reports
        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
          AND deleted_at IS NULL
        GROUP BY DATE(created_at)
        ORDER BY date;
    """)
    usage_over_time = [{"date": row[0].isoformat(), "count": row[1]} for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": {
                "total_reports": total_reports,
                "avg_usage_per_user": avg_usage_per_user,
                "usage_over_time": usage_over_time,
            }
        }
    )


@router.get("/metrics/subscription")
def get_subscription_metrics(current_user: dict = Depends(require_admin)):
    conn = test_database_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.name, COUNT(py.id) AS user_count
            FROM plans p
            LEFT JOIN payments py ON py.plan_id = p.id 
            WHERE p.name <> 'Basic'
            GROUP BY p.name
            ORDER BY p.name;
        """)
        rows = cur.fetchall()

    users_per_plan = [{"name": row[0], "value": row[1]} for row in rows]

    return {"success": True, "data": {"users_per_plan": users_per_plan}}