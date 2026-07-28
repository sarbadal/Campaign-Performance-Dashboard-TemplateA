from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any
from urllib.parse import urlparse

from flask import current_app, redirect, request, session, url_for

from .common import _as_clean_str


AUTH_SESSION_KEY = "app_authenticated"


def _is_auth_enabled() -> bool:
    app_password = _as_clean_str(current_app.config.get("APP_PASSWORD", ""))
    app_password_hash = _as_clean_str(current_app.config.get("APP_PASSWORD_HASH", ""))
    return bool(app_password or app_password_hash)


def _is_authenticated() -> bool:
    if not _is_auth_enabled():
        return True
    return bool(session.get(AUTH_SESSION_KEY, False))


def _is_safe_next_url(target: str) -> bool:
    parsed = urlparse(target)
    return not parsed.netloc and parsed.path.startswith("/")


def _build_login_redirect():
    next_url = request.full_path if request.query_string else request.path
    return redirect(url_for("dashboard.login", next=next_url.rstrip("?")))


def _require_authenticated(view_func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view_func)
    def _wrapped(*args: Any, **kwargs: Any):
        if _is_authenticated():
            return view_func(*args, **kwargs)
        return _build_login_redirect()

    return _wrapped