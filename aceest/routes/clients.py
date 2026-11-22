"""Client management: HTML pages and JSON API."""
from flask import Blueprint, abort, flash, jsonify, render_template, request

from aceest import models
from aceest.routes import back_to_client, client_not_found
from aceest.auth import require_login, role_required
from aceest.fitness import WORKOUT_TYPES, ValidationError, calculate_bmi
from aceest.generator import LEVELS
from aceest.programs import get_program, list_programs

bp = Blueprint("clients", __name__)
bp.before_request(require_login)


# ---------- HTML ----------
def _render_clients():
    return render_template("clients.html", clients=models.list_clients(), programs=list_programs())


@bp.route("/clients", methods=["GET"])
def clients_page():
    return _render_clients()


@bp.route("/clients", methods=["POST"])
def save_client_form():
    try:
        client = models.save_client(request.form)
    except ValidationError as exc:
        flash(str(exc), "error")
        return _render_clients()
    flash(f"Client {client['name']} saved", "info")
    return back_to_client(client["name"])


@bp.route("/clients/<name>", methods=["GET"])
def client_page(name):
    summary = models.client_summary(name)
    if summary is None:
        abort(404)
    client = summary["client"]
    try:
        bmi = calculate_bmi(client["height"], client["weight"])
    except ValidationError:
        bmi = None
    return render_template(
        "client.html",
        client=client,
        summary=summary,
        bmi=bmi,
        program=get_program(client["program"]),
        progress=models.list_progress(name),
        metrics=models.list_metrics(name),
        workouts=models.list_workouts(name),
        plan=models.latest_plan(name),
        levels=LEVELS,
        membership=models.get_membership(name),
        workout_types=WORKOUT_TYPES,
        programs=list_programs(),
    )


@bp.route("/clients/<name>/progress", methods=["POST"])
def client_progress_form(name):
    if models.get_client(name) is None:
        abort(404)
    try:
        models.add_progress(name, request.form.get("adherence"), request.form.get("week"))
        flash("Weekly progress logged", "info")
    except ValidationError as exc:
        flash(str(exc), "error")
    return back_to_client(name)


# ---------- JSON API ----------
@bp.route("/api/clients", methods=["GET"])
def api_list_clients():
    return jsonify(models.list_clients())


@bp.route("/api/clients", methods=["POST"])
def api_save_client():
    try:
        client = models.save_client(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(client), 201


@bp.route("/api/clients/<name>", methods=["GET"])
def api_get_client(name):
    client = models.get_client(name)
    if client is None:
        return client_not_found()
    return jsonify(client)


@bp.route("/api/clients/<name>", methods=["DELETE"])
@role_required("Admin")
def api_delete_client(name):
    if not models.delete_client(name):
        return client_not_found()
    return "", 204


@bp.route("/api/clients/<name>/progress", methods=["GET"])
def api_list_progress(name):
    if models.get_client(name) is None:
        return client_not_found()
    return jsonify(models.list_progress(name))


@bp.route("/api/clients/<name>/progress", methods=["POST"])
def api_add_progress(name):
    if models.get_client(name) is None:
        return client_not_found()
    payload = request.get_json(silent=True) or {}
    try:
        entry = models.add_progress(name, payload.get("adherence"), payload.get("week"))
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(entry), 201
