"""Application configuration, driven by environment variables."""
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _read_version():
    version_file = BASE_DIR / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


class Config:
    APP_NAME = "ACEest Fitness & Gym"
    APP_VERSION = os.environ.get("APP_VERSION") or _read_version()
    # Label used by the deployment strategies (blue/green, stable/canary, A/B)
    DEPLOY_TRACK = os.environ.get("DEPLOY_TRACK") or "stable"
    # Must be supplied (Kubernetes Secret) when running more than one worker/pod.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME") or "admin"
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
    DATABASE_PATH = os.environ.get("DATABASE_PATH") or str(BASE_DIR / "instance" / "aceest.db")
    TESTING = False
