from fastapi import HTTPException, UploadFile
from datetime import datetime
import os
import base64
import uuid
from app.database.db_connect import test_database_connection

UPLOAD_DIR = "uploaded_resources"


def save_uploaded_file(file: UploadFile, base_dir=UPLOAD_DIR) -> str:
    os.makedirs(base_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(base_dir, filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    return file_path


def save_base64_file(base64_data: str, base_dir=UPLOAD_DIR) -> str:
    os.makedirs(base_dir, exist_ok=True)
    try:
        header, encoded = base64_data.split(",", 1)
        content_type = header.split(";")[0].split(":")[1]
        ext = content_type.split("/")[-1]
        decoded = base64.b64decode(encoded)

        filename = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(base_dir, filename)

        with open(file_path, "wb") as f:
            f.write(decoded)

        return file_path
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 file format: {str(e)}")


def validate_and_process_file(file_path: str) -> str:
    if file_path and not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"File path invalid or file not found: {file_path}")
    return file_path


def process_file_input(file_path: str = None, uploaded_file: UploadFile = None) -> str:
    if uploaded_file:
        return save_uploaded_file(uploaded_file)
    if file_path:
        if file_path.startswith("data:"):
            return save_base64_file(file_path)
        return validate_and_process_file(file_path)
    return None


from fastapi import HTTPException

def get_resource_by_id(resource_id: int):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, title, content, file_path, file_url, publication_date, publisher, created_at, updated_at, deleted_at
            FROM resources 
            WHERE id = %s
        """, (resource_id,))
        row = cursor.fetchone()

        # Check if resource doesn't exist or is soft-deleted
        if not row or row[-1] is not None:
            raise HTTPException(status_code=404, detail="Resource not found")

        # Build the resource dictionary
        columns = [desc[0] for desc in cursor.description]
        resource = dict(zip(columns, row))  # include deleted_at temporarily

        # Remove the deleted_at field if you don't want to send it to frontend
        resource.pop("deleted_at", None)

        # Add authors
        resource["authors"] = get_authors_for_resource(resource_id)

        return resource

    finally:
        cursor.close()
        conn.close()


def get_authors_for_resource(resource_id: int):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT a.id, a.name, a.title, a.degree, a.affiliation
            FROM authors a
            JOIN resource_authors ra ON a.id = ra.author_id
            WHERE ra.resource_id = %s
        """, (resource_id,))
        
        authors = [
            {
                "id": row[0],
                "name": row[1],
                "title": row[2],
                "degree": row[3],
                "affiliation": row[4]
            }
            for row in cursor.fetchall()
        ]

        return authors
    finally:
        cursor.close()
        conn.close()



def get_all_resources():
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, title, content, file_path, file_url, publication_date, publisher, created_at, updated_at 
            FROM resources 
            WHERE deleted_at IS NULL 
            ORDER BY created_at DESC
        """)
        columns = [desc[0] for desc in cursor.description]
        result = []
        for row in cursor.fetchall():
            resource = dict(zip(columns, row))
            resource["authors"] = get_authors_for_resource(resource["id"])
            result.append(resource)
        return result
    finally:
        cursor.close()
        conn.close()


def get_or_create_author(cursor, author_data: dict):
    cursor.execute("SELECT id FROM authors WHERE name = %s", (author_data["name"],))
    author_row = cursor.fetchone()
    if author_row:
        return author_row[0]

    now = datetime.utcnow()
    cursor.execute("""
        INSERT INTO authors (name, title, degree, affiliation, created_at)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    """, (
        author_data["name"],
        author_data.get("title"),
        author_data.get("degree"),
        author_data.get("affiliation"),
        now
    ))
    return cursor.fetchone()[0]


def link_authors_to_resource(cursor, resource_id: int, authors: list[dict]):
    cursor.execute("DELETE FROM resource_authors WHERE resource_id = %s", (resource_id,))
    for author_data in authors:
        author_id = get_or_create_author(cursor, author_data)
        cursor.execute("INSERT INTO resource_authors (resource_id, author_id) VALUES (%s, %s)", (resource_id, author_id))

def update_resource(file: UploadFile, base_dir=UPLOAD_DIR) -> str:
    os.makedirs(base_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(base_dir, filename)
    
    file.file.seek(0)
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    file.file.close()
    return file_path


def create_resource(resource_data: dict, uploaded_file: UploadFile = None):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        now = datetime.utcnow()

        file_path = process_file_input(resource_data.get("file_path"), uploaded_file)

        pub_date_str = resource_data.get("publication_date")
        publication_date = None
        if pub_date_str:
            try:
                publication_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid publication_date format, use YYYY-MM-DD")

        cursor.execute("""
            INSERT INTO resources (title, content, file_path, file_url, publication_date, publisher, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            resource_data["title"],
            resource_data["content"],
            file_path,
            resource_data.get("file_url"),
            publication_date,
            resource_data.get("publisher"),
            now,
            now,
        ))
        new_id = cursor.fetchone()[0]

        authors = resource_data.get("authors", [])
        if authors:
            link_authors_to_resource(cursor, new_id, authors)

        conn.commit()
        return get_resource_by_id(new_id)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()


def soft_delete_resource(resource_id: int):
    conn = test_database_connection()
    cursor = conn.cursor()
    try:
        _ = get_resource_by_id(resource_id)
        now = datetime.utcnow()
        cursor.execute("UPDATE resources SET deleted_at = %s WHERE id = %s", (now, resource_id))
        conn.commit()
        return {"message": "Resource deleted"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()
