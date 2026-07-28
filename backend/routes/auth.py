from __future__ import annotations

import hmac

from flask import current_app, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .utils.auth import (
    AUTH_SESSION_KEY,
    _is_auth_enabled,
    _is_authenticated,
    _is_safe_next_url,
)
from .utils.common import (
    TOP_LEVEL_FILTERS_SESSION_KEY,
    _as_clean_str,
    dashboard_bp,
)


def _normalize_safe_next_target(raw_target: object) -> str:
    next_target = _as_clean_str(raw_target)
    return next_target if next_target and _is_safe_next_url(next_target) else ""


def _is_valid_password(entered_password: str) -> bool:
    configured_hash = _as_clean_str(current_app.config.get("APP_PASSWORD_HASH", ""))
    configured_plain = _as_clean_str(current_app.config.get("APP_PASSWORD", ""))

    if configured_hash:
        return check_password_hash(configured_hash, entered_password)
    if configured_plain:
        return hmac.compare_digest(configured_plain, entered_password)
    return False


def _login_success_response(next_target: str):
    session[AUTH_SESSION_KEY] = True
    session.modified = True
    return redirect(next_target) if next_target else redirect(url_for("dashboard.dashboard"))


def _clear_auth_session_state() -> None:
    session.pop(AUTH_SESSION_KEY, None)
    session.pop(TOP_LEVEL_FILTERS_SESSION_KEY, None)
    session.modified = True


def _logout_redirect_response():
    if _is_auth_enabled():
        return redirect(url_for("dashboard.login"))
    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/login", methods=["GET", "POST"])
def login():
    if not _is_auth_enabled():
        return redirect(url_for("dashboard.dashboard"))

    if _is_authenticated():
        next_target = _normalize_safe_next_target(request.args.get("next", ""))
        if next_target:
            return redirect(next_target)
        return redirect(url_for("dashboard.dashboard"))

    next_target = _normalize_safe_next_target(request.args.get("next", ""))
    error_message = ""

    if request.method == "POST":
        entered_password = _as_clean_str(request.form.get("password", ""))
        posted_next = _normalize_safe_next_target(request.form.get("next", ""))
        if posted_next:
            next_target = posted_next

        if _is_valid_password(entered_password):
            return _login_success_response(next_target)

        error_message = "Invalid app password."

    return render_template(
        "login.html",
        error_message=error_message,
        next_target=next_target,
    )


@dashboard_bp.post("/logout")
def logout():
    _clear_auth_session_state()
    return _logout_redirect_response()