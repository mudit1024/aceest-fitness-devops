"""Body metrics, workout logging, BMI and client summary (from release 2.2)."""
from flask import Blueprint, abort, flash, jsonify, redirect, request, url_for

from aceest import models
from aceest.auth import require_login
from aceest.fitness import ValidationError, calculate_bmi

bp = Blueprint("tracking", __name__)
bp.before_request(require_login)


def _client_or_404(name):
    client = models.get_client(name)
    if client is None:
        abort(404)
    return client


def _not_found():
    return jsonify({"error": "client not found"}), 404


# ---------- HTML form handlers ----------
@bp.route("/clients/<name>/metrics", methods=["POST"])
def metrics_form(name):
    _client_or_404(name)
    try:
        models.add_metric(name, request.form)
        flash("Body metrics logged", "info")
    except ValidationError as exc:
        flash(str(exc), "error")
    return redirect(url_for("clients.client_page", name=name))


@bp.route("/clients/<name>/workouts", methods=["POST"])
def workouts_form(name):
    _client_or_404(name)
    data = dict(request.form)
    if data.get("exercise_name"):
        data["exercises"] = [{
            "name": data.get("exercise_name"),
            "sets": data.get("exercise_sets"),
            "reps": data.get("exercise_reps"),
            "weight": data.get("exercise_weight"),
        }]
    try:
        models.add_workout(name, data)
        flash("Workout logged", "info")
    except ValidationError as exc:
        flash(str(exc), "error")
    return redirect(url_for("clients.client_page", name=name))


# ---------- JSON API ----------
@bp.route("/api/clients/<name>/metrics", methods=["GET"])
def api_list_metrics(name):
    if models.get_client(name) is None:
        return _not_found()
    return jsonify(models.list_metrics(name))


@bp.route("/api/clients/<name>/metrics", methods=["POST"])
def api_add_metric(name):
    if models.get_client(name) is None:
        return _not_found()
    try:
        metric = models.add_metric(name, request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(metric), 201


@bp.route("/api/clients/<name>/workouts", methods=["GET"])
def api_list_workouts(name):
    if models.get_client(name) is None:
        return _not_found()
    return jsonify(models.list_workouts(name))


@bp.route("/api/clients/<name>/workouts", methods=["POST"])
def api_add_workout(name):
    if models.get_client(name) is None:
        return _not_found()
    try:
        workout = models.add_workout(name, request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(workout), 201


@bp.route("/api/clients/<name>/bmi", methods=["GET"])
def api_bmi(name):
    client = models.get_client(name)
    if client is None:
        return _not_found()
    try:
        return jsonify(calculate_bmi(client["height"], client["weight"]))
    except ValidationError:
        return jsonify({"error": "valid height and weight are required"}), 400


@bp.route("/api/clients/<name>/summary", methods=["GET"])
def api_summary(name):
    summary = models.client_summary(name)
    if summary is None:
        return _not_found()
    return jsonify(summary)
