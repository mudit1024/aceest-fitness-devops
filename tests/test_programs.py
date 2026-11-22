from aceest.programs import PROGRAMS, get_program, list_programs


def test_catalogue_contains_three_programs():
    assert set(PROGRAMS) == {"FL", "MG", "BG"}


def test_every_program_has_workout_diet_and_color():
    for program in PROGRAMS.values():
        assert program["workout"]
        assert program["diet"]
        assert program["color"].startswith("#")


def test_list_programs_returns_codes_and_names():
    codes = [p["code"] for p in list_programs()]
    assert codes == ["FL", "MG", "BG"]


def test_get_program_is_case_insensitive():
    assert get_program("fl")["name"] == "Fat Loss (FL)"


def test_get_program_unknown_returns_none():
    assert get_program("XX") is None
    assert get_program("") is None
