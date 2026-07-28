"""Route blueprints for the app."""

from .utils import dashboard_bp

# Import modules so route decorators are registered on the shared blueprint.
from . import auth, dashboard, deep_dive  # noqa: F401

__all__ = ["dashboard_bp"]
