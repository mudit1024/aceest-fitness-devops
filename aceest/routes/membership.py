"""Membership billing and the gym dashboard (release 3.2)."""
from flask import Blueprint, abort, flash, jsonify, render_template, request

from aceest import models
from aceest.routes import back_to_client, client_not_found
from aceest.auth import require_login
from aceest.fitness import ValidationError
from aceest.programs import SITE_METRICS

bp = Blueprint("membership", __name__)
bp.before_request(require_login)


@bp.route("/dashboard", methods=["GET"])
def dashboard():
    return render_template("dashboard.html", stats=models.dashboard_stats(), site=SITE_METRICS)


@bp.route("/clients/<name>/membership", methods=["POST"])
def renew_form(name):
    if models.get_client(name) is None:
        abort(404)
    try:
        result = models.renew_membership(name, request.form.get("months"))
        flash(f"Membership renewed until {result['membership_end']}", "info")
    except ValidationError as exc:
        flash(str(exc), "error")
    return back_to_client(name)


@bp.route("/api/dashboard", methods=["GET"])
def api_dashboard():
    return jsonify(models.dashboard_stats())


@bp.route("/api/clients/<name>/membership", methods=["GET"])
def api_membership(name):
    membership = models.get_membership(name)
    if membership is None:
        return client_not_found()
    return jsonify(membership)


@bp.route("/api/clients/<name>/membership", methods=["POST"])
def api_renew(name):
    if models.get_client(name) is None:
        return client_not_found()
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(models.renew_membership(name, payload.get("months"))), 200
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
