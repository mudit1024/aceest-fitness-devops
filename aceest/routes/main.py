"""Public pages, programme catalogue and operational endpoints."""
from flask import Blueprint, abort, current_app, flash, jsonify, render_template, request
from flask_wtf.csrf import generate_csrf

from aceest.fitness import ValidationError, estimate_calories, validate_adherence
from aceest.programs import SITE_METRICS, get_program, list_programs

bp = Blueprint("main", __name__)


@bp.route("/", methods=["GET"])
def index():
    return render_template("index.html", programs=list_programs(), metrics=SITE_METRICS)


@bp.route("/programs/<code>", methods=["GET"])
def program_page(code):
    program = get_program(code)
    if program is None:
        abort(404)
    return render_template("program.html", program=program)


@bp.route("/api/programs", methods=["GET"])
def api_programs():
    return jsonify(list_programs())


@bp.route("/api/programs/<code>", methods=["GET"])
def api_program(code):
    program = get_program(code)
    if program is None:
        return jsonify({"error": f"Unknown program '{code}'"}), 404
    return jsonify(program)


@bp.route("/calculator", methods=["GET", "POST"])
def calculator():
    result = None
    form = request.form if request.method == "POST" else {}
    if request.method == "POST":
        try:
            name = form.get("name", "").strip()
            if not name:
                raise ValidationError("name is required")
            result = {
                "name": name,
                "program": get_program(form.get("program")),
                "calories": estimate_calories(form.get("weight"), form.get("program")),
                "adherence": validate_adherence(form.get("adherence", 0)),
            }
        except ValidationError as exc:
            flash(str(exc), "error")
            result = None
    return render_template("calculator.html", programs=list_programs(), form=form, result=result)


@bp.route("/api/calories", methods=["GET"])
def api_calories():
    program = request.args.get("program", "")
    try:
        calories = estimate_calories(request.args.get("weight"), program)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"program": program.upper(), "calories": calories})


@bp.route("/api/csrf-token", methods=["GET"])
def api_csrf_token():
    """API clients send this value back in the X-CSRFToken header on writes."""
    return jsonify({"csrf_token": generate_csrf()})


@bp.route("/health", methods=["GET"])
def health():
    """Liveness/readiness probe used by Kubernetes."""
    return jsonify({"status": "ok"})


@bp.route("/version", methods=["GET"])
def version():
    """Reports which build is serving the request (used to verify rollouts)."""
    return jsonify(
        {
            "app": current_app.config["APP_NAME"],
            "version": current_app.config["APP_VERSION"],
            "track": current_app.config["DEPLOY_TRACK"],
        }
    )
