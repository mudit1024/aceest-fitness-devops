import pytest

from aceest.fitness import ValidationError, estimate_calories, validate_adherence


@pytest.mark.parametrize("program,expected", [("FL", 1760), ("MG", 2800), ("BG", 2080)])
def test_estimate_calories_uses_program_factor(program, expected):
    assert estimate_calories(80, program) == expected


def test_estimate_calories_accepts_strings_and_lowercase():
    assert estimate_calories("70.5", "fl") == int(70.5 * 22)


@pytest.mark.parametrize("weight", [0, -5, 401, "abc", None])
def test_estimate_calories_rejects_bad_weight(weight):
    with pytest.raises(ValidationError):
        estimate_calories(weight, "FL")


def test_estimate_calories_rejects_unknown_program():
    with pytest.raises(ValidationError):
        estimate_calories(80, "XX")


@pytest.mark.parametrize("value,expected", [(0, 0), ("55", 55), (100, 100)])
def test_validate_adherence_ok(value, expected):
    assert validate_adherence(value) == expected


@pytest.mark.parametrize("value", [-1, 101, "high", None])
def test_validate_adherence_rejects(value):
    with pytest.raises(ValidationError):
        validate_adherence(value)
