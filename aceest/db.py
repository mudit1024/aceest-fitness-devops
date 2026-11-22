"""SQLite persistence layer (one connection per request)."""
import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        age INTEGER,
        height REAL,
        weight REAL,
        program TEXT,
        calories INTEGER,
        target_weight REAL,
        target_adherence INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT NOT NULL,
        week TEXT NOT NULL,
        adherence INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT NOT NULL,
        date TEXT NOT NULL,
        workout_type TEXT NOT NULL,
        duration_min INTEGER,
        notes TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        sets INTEGER,
        reps INTEGER,
        weight REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT NOT NULL,
        date TEXT NOT NULL,
        weight REAL,
        waist REAL,
        bodyfat REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        plan_json TEXT NOT NULL
    )
    """,
]


# Columns added after the original schema; applied with ALTER TABLE so that
# databases created by older releases are upgraded in place.
MIGRATIONS = (
    ("clients", "membership_end", "ALTER TABLE clients ADD COLUMN membership_end TEXT"),
)


def _migrate(conn):
    for table, column, statement in MIGRATIONS:
        existing = {row[1] for row in conn.execute("SELECT * FROM pragma_table_info(?)", (table,))}
        if column not in existing:
            conn.execute(statement)


BUSY_TIMEOUT_SECONDS = 30


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"], timeout=BUSY_TIMEOUT_SECONDS)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create tables, apply migrations and seed the admin user.

    Several processes can start at the same time (gunicorn workers, or pods of
    different releases sharing one volume during a rollout). ``BEGIN IMMEDIATE``
    takes SQLite's write lock up front so initialisation runs one process at a
    time; the others wait and then find everything already in place.
    """
    path = Path(app.config["DATABASE_PATH"])
    path.parent.mkdir(parents=True, exist_ok=True)
    from aceest.auth import seed_admin

    conn = sqlite3.connect(path, timeout=BUSY_TIMEOUT_SECONDS, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        for statement in SCHEMA:
            conn.execute(statement)
        _migrate(conn)
        seed_admin(conn, app)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    app.teardown_appcontext(close_db)
