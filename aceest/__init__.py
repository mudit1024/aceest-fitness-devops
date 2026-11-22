"""ACEest Fitness & Gym - Flask application package."""
from flask import Flask, session
from flask_wtf.csrf import CSRFProtect

from aceest.config import Config

csrf = CSRFProtect()


def create_app(config_object=Config, **overrides):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.config.update(overrides)

    from aceest import auth, db
    from aceest.routes import clients, main, membership, tracking

    csrf.init_app(app)
    db.init_db(app)
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(clients.bp)
    app.register_blueprint(tracking.bp)
    app.register_blueprint(membership.bp)

    @app.context_processor
    def inject_build_info():
        return {
            "app_version": app.config["APP_VERSION"],
            "deploy_track": app.config["DEPLOY_TRACK"],
            "current_user": session.get("user"),
            "current_role": session.get("role"),
        }

    return app
