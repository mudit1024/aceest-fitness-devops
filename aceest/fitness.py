"""Pure fitness calculations shared by the web UI and the JSON API."""
from aceest.programs import PROGRAMS


class ValidationError(ValueError):
    """Raised when user supplied values are outside the accepted range."""


def _positive_number(value, field, maximum):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number") from None
    if not 0 < number <= maximum:
        raise ValidationError(f"{field} must be between 0 and {maximum}")
    return number


def estimate_calories(weight_kg, program_code):
    """Daily calorie target = body weight (kg) x programme calorie factor."""
    weight = _positive_number(weight_kg, "weight", 400)
    program = PROGRAMS.get((program_code or "").upper())
    if program is None:
        raise ValidationError(f"unknown program '{program_code}'")
    return int(weight * program["calorie_factor"])


def validate_adherence(value):
    """Adherence is a whole percentage between 0 and 100."""
    try:
        adherence = int(value)
    except (TypeError, ValueError):
        raise ValidationError("adherence must be an integer") from None
    if not 0 <= adherence <= 100:
        raise ValidationError("adherence must be between 0 and 100")
    return adherence
