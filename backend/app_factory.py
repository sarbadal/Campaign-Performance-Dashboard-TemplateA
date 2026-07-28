from __future__ import annotations

from urllib.parse import quote, urlencode

from flask import Flask
from flask import url_for

from .config import Config
from .routes import dashboard_bp


TEMPLATE_FOLDER = "templates"
GCS_BASE_URL = "https://storage.googleapis.com"


def create_app() -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__, template_folder=TEMPLATE_FOLDER)
    app.config.from_mapping(Config().to_env_dict())

    @app.context_processor
    def inject_static_url_helper():
        """Inject a helper function to generate static URLs with optional query parameters."""

        def static_url(filename: str, **query_params: str) -> str:
            """Generate a static URL with optional query parameters."""
            env_type = str(app.config.get("ENV_TYPE", "dev")).strip().lower()

            if env_type.casefold() not in ["prod", "production"]:
                return url_for("static", filename=filename, **query_params)

            static_base_url = str(app.config.get("STATIC_BASE_URL", "")).strip().rstrip("/")
            static_bucket = str(app.config.get("STATIC_BUCKET", "")).strip()

            if not (static_base_url or static_bucket):
                return url_for("static", filename=filename, **query_params)

            base_root = static_base_url or f"{GCS_BASE_URL}/{static_bucket}"
            base = f"{base_root}/static"

            encoded_filename = "/".join(quote(part) for part in str(filename).split("/"))
            query = urlencode(query_params, doseq=True)
            return f"{base}/{encoded_filename}" if not query else f"{base}/{encoded_filename}?{query}"

        return {
            "static_url": static_url,
        }

    app.register_blueprint(dashboard_bp)
    return app
