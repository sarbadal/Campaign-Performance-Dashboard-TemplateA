from __future__ import annotations

from backend.app_factory import create_app

app = create_app()


def entry_point(request):
    """Entry point for Google Cloud Function"""
    return app


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5055, debug=True)
