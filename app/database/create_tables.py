from app.database.db_connect import test_database_connection

def table_exists(cursor, table_name):
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = %s
        );
    """, (table_name,))
    return cursor.fetchone()[0]

def create_tables():
    try:
        conn = test_database_connection()
        if not conn:
            return
        cursor = conn.cursor()

        tables = {
            "plans": """
                CREATE TABLE plans (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(20) UNIQUE NOT NULL,
                    description TEXT,
                    price_rs INTEGER NOT NULL,
                    duration_days INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """,
            "users": """
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    phone VARCHAR(15) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    roles VARCHAR(10) NOT NULL DEFAULT 'user',
                    subscription_status VARCHAR(20) DEFAULT 'inactive',
                    plan_id INTEGER REFERENCES plans(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP
                );
            """,
            "payments": """
                CREATE TABLE payments (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    plan_id INTEGER REFERENCES plans(id),
                    amount FLOAT NOT NULL,
                    date DATE NOT NULL,
                    expiry_date DATE NOT NULL,
                    khalti_token VARCHAR(255) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP
                );
            """,
            "resources": """
                CREATE TABLE resources (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    file_path TEXT NULL,
                    file_url TEXT NULL,
                    publication_date DATE,
                    publisher VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP
                );
            """,
            "authors": """
                CREATE TABLE authors (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    title VARCHAR(50) NULL,
                    degree VARCHAR(100) NULL,
                    affiliation VARCHAR(255) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """,

            "resource_authors": """
                CREATE TABLE resource_authors (
                    resource_id INTEGER REFERENCES resources(id) ON DELETE CASCADE,
                    author_id INTEGER REFERENCES authors(id) ON DELETE CASCADE,
                    PRIMARY KEY (resource_id, author_id)
                );
            """,

            "reports": """
                CREATE TABLE reports (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    submitted_document TEXT,
                    unique_score FLOAT NOT NULL,
                    total_exact_score FLOAT NOT NULL,
                    total_partial_score FLOAT NOT NULL,
                    words INTEGER,
                    characters INTEGER,
                    citation_status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """,

            "notifications": """
                CREATE TABLE notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    event_type VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP
                );
            """,
            "blacklisted_tokens" : """
                CREATE TABLE blacklisted_tokens (
                    id SERIAL PRIMARY KEY,
                    token TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                );
            """,
            # "password_reset_tokens": """
            #     CREATE TABLE password_reset_tokens (
            #         id SERIAL PRIMARY KEY,
            #         user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            #         otp_code VARCHAR(10) NOT NULL,
            #         expires_at TIMESTAMP NOT NULL,
            #         used BOOLEAN DEFAULT FALSE,
            #         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            #     );
            # """,
            "khalti_payments" :"""
                CREATE TABLE khalti_payments (
                    id SERIAL PRIMARY KEY,
                    pidx VARCHAR UNIQUE NOT NULL,
                    user_id INT NOT NULL,
                    plan_id INT NOT NULL,
                    amount INT NOT NULL,
                    status VARCHAR DEFAULT 'initiated',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """,
        }

        for name, ddl in tables.items():
            if not table_exists(cursor, name):
                cursor.execute(ddl)
                print(f"✅ Created table '{name}'")
            else:
                print(f"ℹ️ Table '{name}' already exists")

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
