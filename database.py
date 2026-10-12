import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("tasks.db")


def init_db():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
            )
        """)


def save_task(user_id, title):
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (user_id, title) VALUES (?, ?)",
            (user_id, title)
        )
        return cursor.lastrowid


def get_tasks(user_id):
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
                        "SELECT id, title, done FROM tasks WHERE user_id = ? ORDER BY id",
            (user_id,)
        )
        return cursor.fetchall()

def complete_task(user_id, task_id):
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET done = 1
            WHERE id = ? AND user_id = ? AND done = 0
            """,
            (task_id, user_id)
        )
        return cursor.rowcount > 0


def delete_task(user_id, task_id):
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id)
        )
        return cursor.rowcount > 0
def get_stats(user_id: int):
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(done), 0)
            FROM tasks
            WHERE user_id = ?
            """,
            (user_id,)
        )

        total, completed = cursor.fetchone()
        active = total - completed

        return total, completed, active