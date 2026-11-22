"""Workout plan generator (port of the 3.1 programme generator)."""
import secrets

from aceest.fitness import ValidationError

FULL_BODY = "Full Body"

EXERCISE_POOL = {
    "Strength": ["Squat", "Deadlift", "Bench Press", "Overhead Press", "Pull-Up", "Barbell Row"],
    "Hypertrophy": ["Leg Press", "Incline Dumbbell Press", "Lat Pulldown", "Lateral Raise",
                    "Bicep Curl", "Tricep Extension"],
    "Conditioning": ["Running", "Cycling", "Rowing", "Burpees", "Jump Rope", "Kettlebell Swings"],
    FULL_BODY: ["Push-Up", "Pull-Up", "Lunge", "Plank", "Dumbbell Row", "Dumbbell Press"],
}

PROGRAM_FOCUS = {"FL": "Conditioning", "MG": "Hypertrophy", "BG": FULL_BODY}

LEVELS = {
    "beginner": {"sets": (2, 3), "reps": (8, 12), "days": 3},
    "intermediate": {"sets": (3, 4), "reps": (8, 15), "days": 4},
    "advanced": {"sets": (4, 5), "reps": (6, 15), "days": 5},
}

WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def generate_plan(program_code, level, rng=None):
    """Build a weekly plan for a programme and experience level.

    ``rng`` can be any object with ``sample`` and ``randint`` (tests pass a
    seeded ``random.Random``); by default the OS entropy source is used.
    """
    rng = rng or secrets.SystemRandom()
    level_key = (level or "").strip().lower()
    if level_key not in LEVELS:
        raise ValidationError("level must be one of " + ", ".join(LEVELS))
    settings = LEVELS[level_key]
    focus = PROGRAM_FOCUS.get((program_code or "").upper(), FULL_BODY)
    per_day = 3 if settings["days"] < 4 else 4

    plan = []
    for day in WEEK_DAYS[: settings["days"]]:
        for exercise in rng.sample(EXERCISE_POOL[focus], k=per_day):
            plan.append({
                "day": day,
                "exercise": exercise,
                "sets": rng.randint(*settings["sets"]),
                "reps": rng.randint(*settings["reps"]),
            })
    return {"focus": focus, "level": level_key, "days": settings["days"], "plan": plan}
