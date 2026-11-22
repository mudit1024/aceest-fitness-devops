"""Data access functions for clients and their weekly progress."""
import json
from datetime import date, datetime, timezone

from aceest.db import get_db
from aceest.fitness import WORKOUT_TYPES, ValidationError, estimate_calories, validate_adherence
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
    db.execute("DELETE FROM workouts WHERE client_name = ?", (name,))
    db.execute("DELETE FROM metrics WHERE client_name = ?", (name,))
    db.execute("DELETE FROM plans WHERE client_name = ?", (name,))
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


def _iso_date(value):
    if value in (None, ""):
        return date.today().isoformat()
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError:
        raise ValidationError("date must be in YYYY-MM-DD format") from None


# ---------- body metrics ----------
def add_metric(name, data):
    metric = {
        "client_name": name,
        "date": _iso_date(data.get("date")),
        "weight": _optional_number(data.get("weight"), float, "weight"),
        "waist": _optional_number(data.get("waist"), float, "waist"),
        "bodyfat": _optional_number(data.get("bodyfat"), float, "bodyfat"),
    }
    if metric["weight"] is None and metric["waist"] is None and metric["bodyfat"] is None:
        raise ValidationError("at least one of weight, waist or bodyfat is required")
    db = get_db()
    db.execute(
        "INSERT INTO metrics (client_name, date, weight, waist, bodyfat) "
        "VALUES (:client_name, :date, :weight, :waist, :bodyfat)",
        metric,
    )
    db.commit()
    return metric


def list_metrics(name):
    rows = get_db().execute(
        "SELECT date, weight, waist, bodyfat FROM metrics WHERE client_name = ? ORDER BY date, id", (name,)
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- workouts ----------
def add_workout(name, data):
    workout_type = (data.get("workout_type") or "").title()
    if workout_type not in WORKOUT_TYPES:
        raise ValidationError("workout_type must be one of " + ", ".join(WORKOUT_TYPES))
    workout = {
        "client_name": name,
        "date": _iso_date(data.get("date")),
        "workout_type": workout_type,
        "duration_min": _optional_number(data.get("duration_min"), int, "duration_min"),
        "notes": (data.get("notes") or "").strip(),
    }
    exercises = []
    for item in data.get("exercises") or []:
        ex_name = (item.get("name") or "").strip()
        if not ex_name:
            raise ValidationError("exercise name is required")
        exercises.append({
            "name": ex_name,
            "sets": _optional_number(item.get("sets"), int, "sets"),
            "reps": _optional_number(item.get("reps"), int, "reps"),
            "weight": _optional_number(item.get("weight"), float, "weight"),
        })
    db = get_db()
    cur = db.execute(
        "INSERT INTO workouts (client_name, date, workout_type, duration_min, notes) "
        "VALUES (:client_name, :date, :workout_type, :duration_min, :notes)",
        workout,
    )
    for ex in exercises:
        db.execute(
            "INSERT INTO exercises (workout_id, name, sets, reps, weight) VALUES (?, ?, ?, ?, ?)",
            (cur.lastrowid, ex["name"], ex["sets"], ex["reps"], ex["weight"]),
        )
    db.commit()
    return {"id": cur.lastrowid, **workout, "exercises": exercises}


def list_workouts(name):
    db = get_db()
    workouts = [dict(r) for r in db.execute(
        "SELECT id, date, workout_type, duration_min, notes FROM workouts "
        "WHERE client_name = ? ORDER BY date DESC, id DESC", (name,)
    ).fetchall()]
    for w in workouts:
        w["exercises"] = [dict(r) for r in db.execute(
            "SELECT name, sets, reps, weight FROM exercises WHERE workout_id = ? ORDER BY id", (w["id"],)
        ).fetchall()]
    return workouts


# ---------- summary ----------
def client_summary(name):
    client = get_client(name)
    if client is None:
        return None
    db = get_db()
    weeks, avg = db.execute(
        "SELECT COUNT(*), AVG(adherence) FROM progress WHERE client_name = ?", (name,)
    ).fetchone()
    total_workouts, total_minutes = db.execute(
        "SELECT COUNT(*), COALESCE(SUM(duration_min), 0) FROM workouts WHERE client_name = ?", (name,)
    ).fetchone()
    metrics = list_metrics(name)
    return {
        "client": client,
        "weeks_logged": weeks,
        "average_adherence": round(avg, 1) if avg is not None else 0,
        "workouts_logged": total_workouts,
        "training_minutes": total_minutes,
        "last_metric": metrics[-1] if metrics else None,
    }


# ---------- generated plans ----------
def save_plan(name, plan):
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db = get_db()
    db.execute(
        "INSERT INTO plans (client_name, created_at, plan_json) VALUES (?, ?, ?)",
        (name, created, json.dumps(plan)),
    )
    db.commit()
    return {**plan, "created_at": created}


def latest_plan(name):
    row = get_db().execute(
        "SELECT created_at, plan_json FROM plans WHERE client_name = ? ORDER BY id DESC LIMIT 1", (name,)
    ).fetchone()
    if row is None:
        return None
    return {**json.loads(row["plan_json"]), "created_at": row["created_at"]}
