"""ACEest Fitness & Gym - Flask application package."""
from flask import Flask

from aceest.config import Config


def create_app(config_object=Config, **overrides):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.config.update(overrides)

    from aceest.routes import main

    app.register_blueprint(main.bp)

    @app.context_processor
    def inject_build_info():
        return {
            "app_version": app.config["APP_VERSION"],
            "deploy_track": app.config["DEPLOY_TRACK"],
        }

    return app
