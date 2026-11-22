"""Training programme catalogue for ACEest Fitness & Gym.

Ported from the original Tkinter release (Aceestver-1.0.py). Each programme
is identified by a short code so it can be used in URLs and API payloads.
"""

PROGRAMS = {
    "FL": {
        "name": "Fat Loss (FL)",
        "workout": [
            "Mon: 5x5 Back Squat + AMRAP",
            "Tue: EMOM 20min Assault Bike",
            "Wed: Bench Press + 21-15-9",
            "Thu: 10RFT Deadlifts/Box Jumps",
            "Fri: 30min Active Recovery",
        ],
        "diet": [
            "B: 3 Egg Whites + Oats Idli",
            "L: Grilled Chicken + Brown Rice",
            "D: Fish Curry + Millet Roti",
            "Target: 2,000 kcal",
        ],
        "color": "#e74c3c",
        "calorie_factor": 22,
    },
    "MG": {
        "name": "Muscle Gain (MG)",
        "workout": [
            "Mon: Squat 5x5",
            "Tue: Bench 5x5",
            "Wed: Deadlift 4x6",
            "Thu: Front Squat 4x8",
            "Fri: Incline Press 4x10",
            "Sat: Barbell Rows 4x10",
        ],
        "diet": [
            "B: 4 Eggs + PB Oats",
            "L: Chicken Biryani (250g Chicken)",
            "D: Mutton Curry + Jeera Rice",
            "Target: 3,200 kcal",
        ],
        "color": "#2ecc71",
        "calorie_factor": 35,
    },
    "BG": {
        "name": "Beginner (BG)",
        "workout": [
            "Circuit Training: Air Squats, Ring Rows, Push-ups",
            "Focus: Technique Mastery & Form (90% Threshold)",
        ],
        "diet": [
            "Balanced Tamil Meals: Idli-Sambar, Rice-Dal, Chapati",
            "Protein: 120g/day",
        ],
        "color": "#3498db",
        "calorie_factor": 26,
    },
}

SITE_METRICS = {
    "capacity_users": 150,
    "area_sq_ft": 10000,
    "break_even_members": 250,
}


def list_programs():
    """Return a list of programme summaries (code + display name)."""
    return [{"code": code, "name": p["name"]} for code, p in PROGRAMS.items()]


def get_program(code):
    """Return the full programme for ``code`` (case-insensitive) or None."""
    if not code:
        return None
    program = PROGRAMS.get(code.upper())
    if program is None:
        return None
    return {"code": code.upper(), **program}
