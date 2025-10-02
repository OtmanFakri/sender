import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

DB_PATH = "jobs.db"

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_database():
    """Initialize the database with job table"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link TEXT NOT NULL,
                text TEXT NOT NULL,
                status TEXT DEFAULT NULL
            )
        """)
        conn.commit()

def save_job(link: str, text: str) -> int:
    """Save a job to database and return the job ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO job (link, text, status) VALUES (?, ?, ?)",
            (link, text, None)
        )
        conn.commit()
        return cursor.lastrowid

def update_job_status(job_id: int, status: str) -> bool:
    """Update job status to 'yes' or other status"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE job SET status = ? WHERE id = ?",
            (status, job_id)
        )
        conn.commit()
        return cursor.rowcount > 0

def delete_job(job_id: int) -> bool:
    """Delete a job from database"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM job WHERE id = ?", (job_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_job(job_id: int) -> Optional[Dict[str, Any]]:
    """Get a job by ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM job WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def get_all_jobs() -> List[Dict[str, Any]]:
    """Get all jobs"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM job")
        return [dict(row) for row in cursor.fetchall()]
