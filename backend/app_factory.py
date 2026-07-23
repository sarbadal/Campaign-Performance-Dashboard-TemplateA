from __future__ import annotations

from flask import Flask

from .config import Config
from .routes.dashboard import dashboard_bp


def create_app() -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__, template_folder="templates")
    app.config.from_object(Config)
    app.register_blueprint(dashboard_bp)
    return app
