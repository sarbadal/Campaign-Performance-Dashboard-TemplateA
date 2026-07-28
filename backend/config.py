from __future__ import annotations

from dataclasses import dataclass, field, fields
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


_BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BASE_DIR / ".env")


@dataclass(init=False)
class CoreConfig:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me").strip() or "dev-secret-change-me"


@dataclass(init=False)
class AuthConfig:
    APP_PASSWORD: str = os.getenv("APP_PASSWORD", "").strip()
    APP_PASSWORD_HASH: str = os.getenv("APP_PASSWORD_HASH", "").strip()


@dataclass(init=False)
class StaticAssetConfig:
    ENV_TYPE: str = _as_choice("ENV_TYPE", "dev", {"dev", "prod"})
    STATIC_BUCKET: str = os.getenv("STATIC_BUCKET", "").strip()
    STATIC_BASE_URL: str = os.getenv("STATIC_BASE_URL", "").strip().rstrip("/")


@dataclass(init=False)
class DataBackendConfig:
    DB_BACKEND: str = os.getenv("DB_BACKEND", "sqlite").strip().lower() or "sqlite"


@dataclass(init=False)
class SqliteConfig:
    SQLITE_DB_FILE: Path = Path(
        os.getenv("SQLITE_DB_FILE", str(_BASE_DIR / "data" / "campaign_performance.db"))
    )


@dataclass(init=False)
class MysqlConfig:
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "127.0.0.1").strip() or "127.0.0.1"
    MYSQL_PORT: int = _as_int("MYSQL_PORT", 3306)
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root").strip() or "root"
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "").strip()
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "campaign_performance").strip() or "campaign_performance"
    MYSQL_TABLE: str = os.getenv("MYSQL_TABLE", "campaign_data").strip() or "campaign_data"
    MYSQL_STATE_TABLE: str = os.getenv("MYSQL_STATE_TABLE", "ingestion_state").strip() or "ingestion_state"


@dataclass(init=False)
class GCSConfig:
    GCS_DATA_BUCKET: str = os.getenv("GCS_DATA_BUCKET", "").strip()
    GCS_DATA_PREFIX: str = os.getenv("GCS_DATA_PREFIX", "").strip()
    GCS_CREDENTIALS_JSON: str = os.getenv("GCS_CREDENTIALS_JSON", "").strip()


@dataclass(init=False)
class FileConfig:
    DASHBOARD_SETTINGS_FILE: Path = Path(
        os.getenv("DASHBOARD_SETTINGS_FILE", str(_BASE_DIR / "settings" / "dashboard_settings.json"))
    )
    FIELD_MAPPING_FILE: Path = Path(
        os.getenv("FIELD_MAPPING_FILE", str(_BASE_DIR / "settings" / "field_mapping.json"))
    )


@dataclass(init=False)
class CacheConfig:
    KPI_CACHE_TTL_SECONDS: int = _as_int("KPI_CACHE_TTL_SECONDS", 300)


@dataclass(init=False)
class BrandingConfig:
    CLIENT_NAME: str = os.getenv("CLIENT_NAME", "Brand Placeholder").strip() or "Brand Placeholder"
    DASHBOARD_KICKER: str = os.getenv("DASHBOARD_KICKER", "Client Dashboard").strip() or "Client Dashboard"
    DASHBOARD_BANNER_TITLE: str = (
        os.getenv("DASHBOARD_BANNER_TITLE", "Campaign Performance Executive Snapshot").strip()
        or "Campaign Performance Executive Snapshot"
    )
    LOGO_IMAGE_PATH: str = os.getenv("LOGO_IMAGE_PATH", "img/client-logo.svg").strip() or "img/client-logo.svg"


@dataclass(init=False)
class FooterConfig:
    FOOTER_TEAM_NAME: str = (
        os.getenv("FOOTER_TEAM_NAME", "Performance Analytics Team").strip()
        or "Performance Analytics Team"
    )
    FOOTER_LOGO_IMAGE_PATH: str = (
        os.getenv("FOOTER_LOGO_IMAGE_PATH", "img/ogs-logo.gif").strip() or "img/ogs-logo.gif"
    )
    SHOW_FOOTER_LOGO: bool = _as_bool("SHOW_FOOTER_LOGO", True)


@dataclass(init=False)
class ThemeConfig:
    BANNER_GRADIENT_START: str = os.getenv("BANNER_GRADIENT_START", "#0b6e4f").strip() or "#0b6e4f"
    BANNER_GRADIENT_MID: str = os.getenv("BANNER_GRADIENT_MID", "#13795c").strip() or "#13795c"
    BANNER_GRADIENT_END: str = os.getenv("BANNER_GRADIENT_END", "#2e8f74").strip() or "#2e8f74"
    DASHBOARD_FONT_FAMILY: str = (
        os.getenv("DASHBOARD_FONT_FAMILY", '"Arial", "Helvetica", sans-serif').strip()
        or '"Arial", "Helvetica", sans-serif'
    )
    KPI_CURRENCY_SYMBOL: str = os.getenv("KPI_CURRENCY_SYMBOL", "RM").strip()


@dataclass(init=False)
class KPIStyleConfig:
    KPI_LABEL_COLOR: str = os.getenv("KPI_LABEL_COLOR", "#56605b").strip() or "#56605b"
    KPI_VALUE_COLOR: str = os.getenv("KPI_VALUE_COLOR", "#0b6e4f").strip() or "#0b6e4f"
    KPI_LABEL_FONT_SIZE: str = os.getenv("KPI_LABEL_FONT_SIZE", "0.9rem").strip() or "0.9rem"
    KPI_VALUE_FONT_SIZE: str = (
        os.getenv("KPI_VALUE_FONT_SIZE", "1.8rem").strip()
        or "1.8rem"
    )


@dataclass(init=False)
class LoadingConfig:
    DASHBOARD_LOADING_TITLE: str = (
        os.getenv("DASHBOARD_LOADING_TITLE", "Loading and preparing your dashboard").strip()
        or "Loading and preparing your dashboard"
    )
    DASHBOARD_LOADING_SUBTITLE: str = (
        os.getenv("DASHBOARD_LOADING_SUBTITLE", "Please wait while we fetch and process the latest data.").strip()
        or "Please wait while we fetch and process the latest data."
    )


@dataclass
class Config:
    """Application configuration assembled via composition of smaller sections."""

    core: CoreConfig = field(default_factory=CoreConfig, repr=False)
    auth: AuthConfig = field(default_factory=AuthConfig, repr=False)
    static_assets: StaticAssetConfig = field(default_factory=StaticAssetConfig, repr=False)
    data_backend: DataBackendConfig = field(default_factory=DataBackendConfig, repr=False)
    sqlite: SqliteConfig = field(default_factory=SqliteConfig, repr=False)
    mysql: MysqlConfig = field(default_factory=MysqlConfig, repr=False)
    gcs: GCSConfig = field(default_factory=GCSConfig, repr=False)
    files: FileConfig = field(default_factory=FileConfig, repr=False)
    cache: CacheConfig = field(default_factory=CacheConfig, repr=False)
    branding: BrandingConfig = field(default_factory=BrandingConfig, repr=False)
    footer: FooterConfig = field(default_factory=FooterConfig, repr=False)
    theme: ThemeConfig = field(default_factory=ThemeConfig, repr=False)
    kpi_style: KPIStyleConfig = field(default_factory=KPIStyleConfig, repr=False)
    loading: LoadingConfig = field(default_factory=LoadingConfig, repr=False)

    def __post_init__(self) -> None:
        self.BASE_DIR = _BASE_DIR
        sections = (
            self.core,
            self.auth,
            self.static_assets,
            self.data_backend,
            self.sqlite,
            self.mysql,
            self.gcs,
            self.files,
            self.cache,
            self.branding,
            self.footer,
            self.theme,
            self.kpi_style,
            self.loading,
        )

        for section in sections:
            for section_field in fields(section):
                key = section_field.name
                if key.isupper():
                    setattr(self, key, getattr(section, key))

    def to_env_dict(self) -> dict[str, object]:
        """Return a plain mapping of uppercase config keys and their values."""
        return {
            key: value
            for key, value in vars(self).items()
            if key.isupper()
        }
