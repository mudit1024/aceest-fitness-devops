"""Client management: HTML pages and JSON API."""
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for

from aceest import models
from aceest.fitness import ValidationError
from aceest.programs import get_program, list_programs

bp = Blueprint("clients", __name__)


# ---------- HTML ----------
@bp.route("/clients", methods=["GET", "POST"])
def clients_page():
    if request.method == "POST":
        try:
            client = models.save_client(request.form)
        except ValidationError as exc:
            flash(str(exc), "error")
        else:
            flash(f"Client {client['name']} saved", "info")
            return redirect(url_for("clients.client_page", name=client["name"]))
    return render_template("clients.html", clients=models.list_clients(), programs=list_programs())


@bp.route("/clients/<name>", methods=["GET"])
def client_page(name):
    client = models.get_client(name)
    if client is None:
        abort(404)
    return render_template(
        "client.html",
        client=client,
        program=get_program(client["program"]),
        progress=models.list_progress(name),
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
    return redirect(url_for("clients.client_page", name=name))


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
        return jsonify({"error": "client not found"}), 404
    return jsonify(client)


@bp.route("/api/clients/<name>", methods=["DELETE"])
def api_delete_client(name):
    if not models.delete_client(name):
        return jsonify({"error": "client not found"}), 404
    return "", 204


@bp.route("/api/clients/<name>/progress", methods=["GET"])
def api_list_progress(name):
    if models.get_client(name) is None:
        return jsonify({"error": "client not found"}), 404
    return jsonify(models.list_progress(name))


@bp.route("/api/clients/<name>/progress", methods=["POST"])
def api_add_progress(name):
    if models.get_client(name) is None:
        return jsonify({"error": "client not found"}), 404
    payload = request.get_json(silent=True) or {}
    try:
        entry = models.add_progress(name, payload.get("adherence"), payload.get("week"))
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(entry), 201
