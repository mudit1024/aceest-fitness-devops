"""Public pages, programme catalogue and operational endpoints."""
from flask import Blueprint, abort, current_app, jsonify, render_template

from aceest.programs import SITE_METRICS, get_program, list_programs

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return render_template("index.html", programs=list_programs(), metrics=SITE_METRICS)


@bp.route("/programs/<code>")
def program_page(code):
    program = get_program(code)
    if program is None:
        abort(404)
    return render_template("program.html", program=program)


@bp.route("/api/programs")
def api_programs():
    return jsonify(list_programs())


@bp.route("/api/programs/<code>")
def api_program(code):
    program = get_program(code)
    if program is None:
        return jsonify({"error": f"Unknown program '{code}'"}), 404
    return jsonify(program)


@bp.route("/health")
def health():
    """Liveness/readiness probe used by Kubernetes."""
    return jsonify({"status": "ok"})


@bp.route("/version")
def version():
    """Reports which build is serving the request (used to verify rollouts)."""
    return jsonify(
        {
            "app": current_app.config["APP_NAME"],
            "version": current_app.config["APP_VERSION"],
            "track": current_app.config["DEPLOY_TRACK"],
        }
    )
