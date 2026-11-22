"""Data access functions for clients and their weekly progress."""
from datetime import date

from aceest.db import get_db
from aceest.fitness import ValidationError, estimate_calories, validate_adherence
from aceest.programs import PROGRAMS


def _optional_number(value, cast, field):
    if value in (None, ""):
        return None
    try:
        number = cast(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number") from None
    if number < 0:
        raise ValidationError(f"{field} must not be negative")
    return number


def clean_client(data):
    """Validate a client payload and derive the calorie target."""
    name = (data.get("name") or "").strip()
    if not name:
        raise ValidationError("name is required")
    program = (data.get("program") or "").upper()
    if program not in PROGRAMS:
        raise ValidationError("program must be one of " + ", ".join(PROGRAMS))
    weight = _optional_number(data.get("weight"), float, "weight")
    client = {
        "name": name,
        "age": _optional_number(data.get("age"), int, "age"),
        "height": _optional_number(data.get("height"), float, "height"),
        "weight": weight,
        "program": program,
        "calories": estimate_calories(weight, program) if weight else None,
        "target_weight": _optional_number(data.get("target_weight"), float, "target_weight"),
        "target_adherence": None,
    }
    if data.get("target_adherence") not in (None, ""):
        client["target_adherence"] = validate_adherence(data["target_adherence"])
    return client


def save_client(data):
    """Insert or update (by name) a client and return the stored record."""
    client = clean_client(data)
    db = get_db()
    db.execute(
        """
        INSERT INTO clients (name, age, height, weight, program, calories, target_weight, target_adherence)
        VALUES (:name, :age, :height, :weight, :program, :calories, :target_weight, :target_adherence)
        ON CONFLICT(name) DO UPDATE SET
            age=excluded.age, height=excluded.height, weight=excluded.weight,
            program=excluded.program, calories=excluded.calories,
            target_weight=excluded.target_weight, target_adherence=excluded.target_adherence
        """,
        client,
    )
    db.commit()
    return get_client(client["name"])


def get_client(name):
    row = get_db().execute("SELECT * FROM clients WHERE name = ?", (name,)).fetchone()
    return dict(row) if row else None


def list_clients():
    rows = get_db().execute("SELECT * FROM clients ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def delete_client(name):
    db = get_db()
    db.execute("DELETE FROM progress WHERE client_name = ?", (name,))
    cur = db.execute("DELETE FROM clients WHERE name = ?", (name,))
    db.commit()
    return cur.rowcount > 0


def current_week_label(today=None):
    today = today or date.today()
    return today.strftime("Week %U - %Y")


def add_progress(name, adherence, week=None):
    adherence = validate_adherence(adherence)
    week = (week or "").strip() or current_week_label()
    db = get_db()
    db.execute(
        "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
        (name, week, adherence),
    )
    db.commit()
    return {"client_name": name, "week": week, "adherence": adherence}


def list_progress(name):
    rows = get_db().execute(
        "SELECT week, adherence FROM progress WHERE client_name = ? ORDER BY id", (name,)
    ).fetchall()
    return [dict(r) for r in rows]
