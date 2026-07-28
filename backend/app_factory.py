from __future__ import annotations

from urllib.parse import quote, urlencode

from flask import Flask
from flask import url_for

from .config import Config
from .routes import dashboard_bp


def create_app() -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__, template_folder="templates")
    app.config.from_object(Config)

    @app.context_processor
    def inject_static_url_helper():
        def static_url(filename: str, **query_params: str) -> str:
            env_type = str(app.config.get("ENV_TYPE", "dev")).strip().lower()
            if env_type != "prod":
                return url_for("static", filename=filename, **query_params)

            static_base_url = str(app.config.get("STATIC_BASE_URL", "")).strip().rstrip("/")
            static_bucket = str(app.config.get("STATIC_BUCKET", "")).strip()

            if static_base_url:
                base = f"{static_base_url}/static"
            elif static_bucket:
                base = f"https://storage.googleapis.com/{static_bucket}/static"
            else:
                return url_for("static", filename=filename, **query_params)

            encoded_filename = "/".join(quote(part) for part in str(filename).split("/"))
            query = urlencode(query_params, doseq=True)
            return f"{base}/{encoded_filename}" if not query else f"{base}/{encoded_filename}?{query}"

        return {
            "static_url": static_url,
        }

    app.register_blueprint(dashboard_bp)
    return app
