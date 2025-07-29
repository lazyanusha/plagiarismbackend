# app/database/init_db.py

from app.database.connfig import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from app.seed.seed_admin import seed_admin_user
from app.database.db_connect import test_database_connection
from app.database.create_tables import create_tables
import psycopg2 # type: ignore
from psycopg2 import sql

from app.seed.seed_plans import seed_plans # type: ignore

def create_database_if_not_exists():
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if not cursor.fetchone():
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            print(f"✅ Database '{DB_NAME}' created")
        else:
            print(f"ℹ️ Database '{DB_NAME}' already exists")

        cursor.close()
        conn.close()

        test_database_connection()
        create_tables()
        seed_admin_user()
        seed_plans()

    except Exception as e:
        print(f"❌ Could not create database: {e}")

if __name__ == "__main__":
    create_database_if_not_exists()
    
