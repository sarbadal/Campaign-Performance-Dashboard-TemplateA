from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def _as_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _as_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _as_choice(name: str, default: str, allowed: set[str]) -> str:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    if raw in allowed:
        return raw
    return default


class Config:
    """Application configuration."""

    BASE_DIR = Path(__file__).resolve().parent.parent
    load_dotenv(BASE_DIR / ".env")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me").strip() or "dev-secret-change-me"
    APP_PASSWORD = os.getenv("APP_PASSWORD", "").strip()
    APP_PASSWORD_HASH = os.getenv("APP_PASSWORD_HASH", "").strip()
    ENV_TYPE = _as_choice("ENV_TYPE", "dev", {"dev", "prod"})
    STATIC_BUCKET = os.getenv("STATIC_BUCKET", "").strip()
    STATIC_BASE_URL = os.getenv("STATIC_BASE_URL", "").strip().rstrip("/")

    DB_BACKEND = os.getenv("DB_BACKEND", "sqlite").strip().lower() or "sqlite"
    SQLITE_DB_FILE = Path(
        os.getenv("SQLITE_DB_FILE", str(BASE_DIR / "data" / "campaign_performance.db"))
    )
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1").strip() or "127.0.0.1"
    MYSQL_PORT = _as_int("MYSQL_PORT", 3306)
    MYSQL_USER = os.getenv("MYSQL_USER", "root").strip() or "root"
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "").strip()
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "campaign_performance").strip() or "campaign_performance"
    MYSQL_TABLE = os.getenv("MYSQL_TABLE", "campaign_data").strip() or "campaign_data"
    MYSQL_STATE_TABLE = os.getenv("MYSQL_STATE_TABLE", "ingestion_state").strip() or "ingestion_state"
    GCS_DATA_BUCKET = os.getenv("GCS_DATA_BUCKET", "").strip()
    GCS_DATA_PREFIX = os.getenv("GCS_DATA_PREFIX", "").strip()
    GCS_CREDENTIALS_JSON = os.getenv("GCS_CREDENTIALS_JSON", "").strip()
    DASHBOARD_SETTINGS_FILE = Path(
        os.getenv("DASHBOARD_SETTINGS_FILE", str(BASE_DIR / "settings" / "dashboard_settings.json"))
    )
    FIELD_MAPPING_FILE = Path(
        os.getenv("FIELD_MAPPING_FILE", str(BASE_DIR / "settings" / "field_mapping.json"))
    )
    KPI_CACHE_TTL_SECONDS = _as_int("KPI_CACHE_TTL_SECONDS", 300)

    CLIENT_NAME = os.getenv("CLIENT_NAME", "Brand Placeholder").strip() or "Brand Placeholder"
    DASHBOARD_KICKER = os.getenv("DASHBOARD_KICKER", "Client Dashboard").strip() or "Client Dashboard"
    DASHBOARD_BANNER_TITLE = (
        os.getenv("DASHBOARD_BANNER_TITLE", "Campaign Performance Executive Snapshot").strip()
        or "Campaign Performance Executive Snapshot"
    )
    LOGO_IMAGE_PATH = os.getenv("LOGO_IMAGE_PATH", "img/client-logo.svg").strip() or "img/client-logo.svg"

    FOOTER_TEAM_NAME = (
        os.getenv("FOOTER_TEAM_NAME", "Performance Analytics Team").strip()
        or "Performance Analytics Team"
    )
    FOOTER_LOGO_IMAGE_PATH = os.getenv("FOOTER_LOGO_IMAGE_PATH", "img/ogs-logo.gif").strip() or "img/ogs-logo.gif"
    SHOW_FOOTER_LOGO = _as_bool("SHOW_FOOTER_LOGO", True)

    BANNER_GRADIENT_START = os.getenv("BANNER_GRADIENT_START", "#0b6e4f").strip() or "#0b6e4f"
    BANNER_GRADIENT_MID = os.getenv("BANNER_GRADIENT_MID", "#13795c").strip() or "#13795c"
    BANNER_GRADIENT_END = os.getenv("BANNER_GRADIENT_END", "#2e8f74").strip() or "#2e8f74"
    DASHBOARD_FONT_FAMILY = (
        os.getenv("DASHBOARD_FONT_FAMILY", '"Arial", "Helvetica", sans-serif').strip()
        or '"Arial", "Helvetica", sans-serif'
    )
    KPI_CURRENCY_SYMBOL = os.getenv("KPI_CURRENCY_SYMBOL", "RM").strip()

    KPI_LABEL_COLOR = os.getenv("KPI_LABEL_COLOR", "#56605b").strip() or "#56605b"
    KPI_VALUE_COLOR = os.getenv("KPI_VALUE_COLOR", "#0b6e4f").strip() or "#0b6e4f"
    KPI_LABEL_FONT_SIZE = os.getenv("KPI_LABEL_FONT_SIZE", "0.9rem").strip() or "0.9rem"
    KPI_VALUE_FONT_SIZE = (
        os.getenv("KPI_VALUE_FONT_SIZE", "1.8rem").strip()
        or "1.8rem"
    )

    DASHBOARD_LOADING_TITLE = (
        os.getenv("DASHBOARD_LOADING_TITLE", "Loading and preparing your dashboard").strip()
        or "Loading and preparing your dashboard"
    )
    DASHBOARD_LOADING_SUBTITLE = (
        os.getenv("DASHBOARD_LOADING_SUBTITLE", "Please wait while we fetch and process the latest data.").strip()
        or "Please wait while we fetch and process the latest data."
    )
