# app/database/db_connect.py

import psycopg2 # type: ignore

from app.database.connfig import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER # type: ignore

def test_database_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print(f"✅ Connected to database '{DB_NAME}'")
        return conn
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        return None
