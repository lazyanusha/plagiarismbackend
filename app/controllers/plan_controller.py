from fastapi import HTTPException
from app.models.plan_model import PlanCreate, PlanUpdate
from app.database.db_connect import test_database_connection
from psycopg2.extras import RealDictCursor # type: ignore

def create_plan(plan: PlanCreate):
    conn = test_database_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            INSERT INTO plans (name, description, price_rs, duration_days)
            VALUES (%s, %s, %s, %s)
            RETURNING *;
        """, (plan.name, plan.description, plan.price_rs, plan.duration_days))
        new_plan = cursor.fetchone()
        conn.commit()
        return new_plan
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()

def get_all_plans():
    conn = test_database_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM plans ORDER BY id;")
    plans = cursor.fetchall()
    cursor.close()
    conn.close()
    return plans

def get_plan(plan_id: int):
    conn = test_database_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM plans WHERE id = %s;", (plan_id,))
    plan = cursor.fetchone()
    cursor.close()
    conn.close()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

def update_plan_partial(plan_id: int, plan_update: PlanUpdate):
    # Get existing plan first (optional but recommended)
    existing_plan = get_plan(plan_id)
    if not existing_plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Merge update fields
    update_data = plan_update.dict(exclude_unset=True)  # only fields passed in request

    # Build SET clause dynamically
    set_clauses = []
    values = []
    for i, (field, value) in enumerate(update_data.items(), start=1):
        set_clauses.append(f"{field} = %s")
        values.append(value)
    values.append(plan_id)

    if not set_clauses:
        # nothing to update
        return existing_plan

    set_clause = ", ".join(set_clauses)
    sql = f"UPDATE plans SET {set_clause} WHERE id = %s RETURNING *;"

    conn = test_database_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(sql, tuple(values))
    updated = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    if not updated:
        raise HTTPException(status_code=404, detail="Plan not found")

    return updated


def delete_plan(plan_id: int):
    conn = test_database_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM plans WHERE id = %s RETURNING id;", (plan_id,))
    deleted = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "Plan deleted"}
