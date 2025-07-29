from app.database.db_connect import test_database_connection
def seed_plans():
    conn = test_database_connection()
    if not conn:
        print("❌ Failed to connect to the database.")
        return False

    cursor = conn.cursor()

    # Predefined plans
    plans = [
        {
            "name": "Basic",
            "description": "Access to basic plagiarism checks with limited features.",
            "price_rs": 0,
            "duration_days": 30
        },
        {
            "name": "Weekly",
            "description": "Unlimited checks with all features and top-tier support for 7 days .",
            "price_rs": 199,
            "duration_days": 7
        },
        {
            "name": "Monthly",
            "description": "Unlimited checks with all features and top-tier support for 30 days.",
            "price_rs": 499,
            "duration_days": 30
        }
        ,
        {
            "name": "Yearly",
            "description": "Unlimited checks with all features and top-tier support for 265 days.",
            "price_rs": 4999,
            "duration_days": 265
        }
    ]

    for plan in plans:
        # Check if plan already exists
        cursor.execute("SELECT id FROM plans WHERE name = %s;", (plan["name"],))
        if cursor.fetchone():
            print(f"ℹ️ Plan '{plan['name']}' already exists.")
            continue

        # Insert plan
        cursor.execute("""
            INSERT INTO plans (name, description, price_rs, duration_days)
            VALUES (%s, %s, %s, %s)
        """, (
            plan["name"],
            plan["description"],
            plan["price_rs"],
            plan["duration_days"]
        ))

        print(f"✅ Inserted plan: {plan['name']}")

    conn.commit()
    cursor.close()
    conn.close()
    return True
