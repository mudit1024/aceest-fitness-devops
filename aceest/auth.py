"""Authentication and role-based access control (from release 3.x)."""
import functools
import logging
import secrets
import sqlite3

from flask import (Blueprint, current_app, flash, jsonify, redirect, render_template, request, session,
                   url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from aceest.db import get_db

log = logging.getLogger(__name__)

bp = Blueprint("auth", __name__)

ROLES = ("Admin", "Trainer")


# ---------- user store ----------
def create_user(username, password, role):
    username = (username or "").strip()
    if not username or not password:
        raise ValueError("username and password are required")
    if role not in ROLES:
        raise ValueError("role must be one of " + ", ".join(ROLES))
    db = get_db()
    db.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, generate_password_hash(password), role),
    )
    db.commit()
    return {"username": username, "role": role}


def authenticate(username, password):
    row = get_db().execute(
        "SELECT username, password_hash, role FROM users WHERE username = ?", ((username or "").strip(),)
    ).fetchone()
    if row and check_password_hash(row["password_hash"], password or ""):
        return {"username": row["username"], "role": row["role"]}
    return None


def seed_admin(conn, app):
    """Create the initial admin account if the users table is empty."""
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        return
    username = app.config["ADMIN_USERNAME"]
    password = app.config["ADMIN_PASSWORD"]
    if not password:
        password = secrets.token_urlsafe(12)
        log.warning("ADMIN_PASSWORD not set - generated one-time admin password: %s", password)
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, 'Admin')",
        (username, generate_password_hash(password)),
    )


# ---------- decorators / guards ----------
def _wants_json():
    return request.path.startswith("/api/")


def require_login():
    """before_request hook for blueprints whose routes all need a signed-in user."""
    if session.get("user"):
        return None
    if _wants_json():
        return jsonify({"error": "authentication required"}), 401
    return redirect(url_for("auth.login", next=request.path))


def role_required(role):
    def decorator(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") != role:
                if _wants_json():
                    return jsonify({"error": f"{role} role required"}), 403
                flash(f"{role} role required", "error")
                return redirect(url_for("clients.clients_page"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def _start_session(user):
    session.clear()
    session["user"] = user["username"]
    session["role"] = user["role"]


def _safe_next(target):
    # Only allow relative redirects inside this site.
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("clients.clients_page")


# ---------- routes ----------
@bp.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@bp.route("/login", methods=["POST"])
def login_submit():
    user = authenticate(request.form.get("username"), request.form.get("password"))
    if user:
        _start_session(user)
        return redirect(_safe_next(request.args.get("next")))
    flash("Invalid credentials", "error")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("main.index"))


@bp.route("/api/login", methods=["POST"])
def api_login():
    payload = request.get_json(silent=True) or {}
    user = authenticate(payload.get("username"), payload.get("password"))
    if not user:
        return jsonify({"error": "invalid credentials"}), 401
    _start_session(user)
    return jsonify(user)


@bp.route("/api/me", methods=["GET"])
def api_me():
    if not session.get("user"):
        return jsonify({"error": "authentication required"}), 401
    return jsonify({"username": session["user"], "role": session["role"]})


@bp.route("/api/users", methods=["POST"])
@role_required("Admin")
def api_create_user():
    payload = request.get_json(silent=True) or {}
    try:
        user = create_user(payload.get("username"), payload.get("password"), payload.get("role", "Trainer"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except sqlite3.IntegrityError as exc:
        current_app.logger.info("user create failed: %s", exc)
        return jsonify({"error": "username already exists"}), 409
    return jsonify(user), 201
