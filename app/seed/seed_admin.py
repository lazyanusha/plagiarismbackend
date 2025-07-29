# app/database/seed_admin.py

import bcrypt
from app.database.db_connect import test_database_connection

def seed_admin_user():
    conn = test_database_connection()
    if not conn:
        return False

    cursor = conn.cursor()
    email = "admin@gmail.com"

    cursor.execute("SELECT id FROM users WHERE email = %s;", (email,))
    if cursor.fetchone():
        print("ℹ️ Admin already exists")
        return True

    hashed_pw = bcrypt.hashpw("Admin@123".encode(), bcrypt.gensalt()).decode()
    cursor.execute("""
        INSERT INTO users (full_name, email, phone, password, roles)
        VALUES (%s, %s, %s, %s, %s)
    """, ("Admin User", email, "admin@gmail.com", hashed_pw, "admin"))

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Admin created")
    return True
