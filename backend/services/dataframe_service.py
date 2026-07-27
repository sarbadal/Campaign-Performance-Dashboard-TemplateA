from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
import re
import time
from urllib.parse import quote_plus

import pandas as pd

from backend.services.db_service import get_sqlite_connection
from backend.services.field_mapping_service import apply_field_mapping, load_field_mapping
from backend.services.mysql_service import get_mysql_connection


_DF_CACHE: dict[str, object] = {
    "expires_at": 0.0,
    "backend": None,
    "source_mtime_ns": None,
    "source_size": None,
    "payload": None,
}


def _quote_mysql_ident(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def _read_mysql_table_as_dataframe(conn, table_name: str) -> pd.DataFrame:
    """Read full MySQL table into a DataFrame without pandas SQL adapters."""
    sql = f"SELECT * FROM {_quote_mysql_ident(table_name)}"
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        description = cur.description or []

    columns = [str(col[0]) for col in description]
    return pd.DataFrame(rows, columns=columns)


def _read_mysql_table_as_dataframe_sqlalchemy(mysql_config: dict[str, object], table_name: str) -> pd.DataFrame | None:
    """Read full MySQL table via SQLAlchemy when available.

    Returns None when SQLAlchemy is not installed so callers can use a fallback.
    """
    try:
        from sqlalchemy import create_engine, text
    except ModuleNotFoundError:
        return None

    user = quote_plus(str(mysql_config.get("user", "root")))
    password = quote_plus(str(mysql_config.get("password", "")))
    host = str(mysql_config.get("host", "127.0.0.1"))
    port = int(mysql_config.get("port", 3306))
    database = quote_plus(str(mysql_config.get("database", "campaign_performance")))

    engine = create_engine(
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4",
        pool_pre_ping=True,
    )
    try:
        sql = f"SELECT * FROM {_quote_mysql_ident(table_name)}"
        with engine.connect() as sql_conn:
            result = sql_conn.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())
        return pd.DataFrame(rows, columns=columns)
    finally:
        engine.dispose()


def _build_gcs_client(gcs_credentials_json: str | None):
    try:
        from google.cloud import storage
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "GCS backend selected but google-cloud-storage is not installed. Install requirements first."
        ) from exc

    raw_credentials = (gcs_credentials_json or "").strip()
    if not raw_credentials:
        return storage.Client()

    try:
        credentials_info = json.loads(raw_credentials)
    except json.JSONDecodeError as exc:
        raise ValueError("GCS_CREDENTIALS_JSON is not valid JSON.") from exc

    try:
        from google.oauth2 import service_account
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "GCS backend selected but google-auth is not installed. Install requirements first."
        ) from exc

    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    project_id = str(credentials_info.get("project_id", "")).strip() or None
    return storage.Client(project=project_id, credentials=credentials)


def _extract_month_sort_key(year_part: str, filename: str) -> tuple[int, int] | None:
    mm_yyyy_match = re.fullmatch(r"(\d{2})\.(\d{4})\.csv", filename)
    if mm_yyyy_match:
        month = int(mm_yyyy_match.group(1))
        year_from_filename = mm_yyyy_match.group(2)
        if year_from_filename != year_part or not (1 <= month <= 12):
            return None
        return (int(year_part), month)

    dd_mm_yyyy_match = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})\.csv", filename)
    if dd_mm_yyyy_match:
        month = int(dd_mm_yyyy_match.group(2))
        year_from_filename = dd_mm_yyyy_match.group(3)
        if year_from_filename != year_part or not (1 <= month <= 12):
            return None
        return (int(year_part), month)

    return None


def _read_gcs_monthly_csvs_as_dataframe(gcs_bucket: str, gcs_prefix: str, gcs_credentials_json: str | None) -> pd.DataFrame:
    bucket_name = gcs_bucket.strip()
    if not bucket_name:
        raise ValueError("GCS_DATA_BUCKET must be configured when DB_BACKEND is 'gcs'.")

    prefix = gcs_prefix.strip().strip("/")
    list_prefix = f"{prefix}/" if prefix else ""

    client = _build_gcs_client(gcs_credentials_json)
    blobs = client.list_blobs(bucket_name, prefix=list_prefix)

    monthly_blobs: list[tuple[int, int, object]] = []
    for blob in blobs:
        blob_name = str(getattr(blob, "name", ""))
        if not blob_name or blob_name.endswith("/"):
            continue

        relative_name = blob_name[len(list_prefix):] if list_prefix and blob_name.startswith(list_prefix) else blob_name
        parts = relative_name.split("/")
        if len(parts) != 2:
            continue

        year_part, filename = parts
        if not re.fullmatch(r"\d{4}", year_part):
            continue

        sort_key = _extract_month_sort_key(year_part, filename)
        if sort_key is None:
            continue

        monthly_blobs.append((sort_key[0], sort_key[1], blob))

    if not monthly_blobs:
        prefix_display = f"{prefix}/" if prefix else ""
        raise ValueError(
            f"No monthly CSV files found in gs://{bucket_name}/{prefix_display}. "
            "Expected files like YYYY/MM.YYYY.csv."
        )

    frames: list[pd.DataFrame] = []
    for _, _, blob in sorted(monthly_blobs, key=lambda item: (item[0], item[1])):
        payload = blob.download_as_bytes()
        frames.append(pd.read_csv(BytesIO(payload)))

    return pd.concat(frames, ignore_index=True, sort=False)


@dataclass
class DataframeRequest:
    db_backend: str
    sqlite_db_file: Path
    mysql_config: dict[str, object]
    field_mapping_file: Path
    cache_ttl_seconds: int = 300
    gcs_bucket: str = ""
    gcs_prefix: str = ""
    gcs_credentials_json: str | None = None


def get_campaign_dataframe(request: DataframeRequest) -> pd.DataFrame:
    """Load campaign data into a reusable pandas DataFrame from configured DB backend."""
    backend = (request.db_backend or "sqlite").strip().lower()
    source_mtime_ns: int | None = None
    source_size: int | None = None

    now = time.time()
    cached = _DF_CACHE.get("payload")
    expires_at = float(_DF_CACHE.get("expires_at", 0.0))
    cached_backend = _DF_CACHE.get("backend")
    cached_source_mtime_ns = _DF_CACHE.get("source_mtime_ns")
    cached_source_size = _DF_CACHE.get("source_size")
    if (
        cached is not None
        and now < expires_at
        and cached_backend == backend
        and cached_source_mtime_ns == source_mtime_ns
        and cached_source_size == source_size
    ):
        return cached  # type: ignore[return-value]

    if backend == "sqlite":
        with get_sqlite_connection(request.sqlite_db_file) as conn:
            dataframe = pd.read_sql_query("SELECT * FROM campaign_data", conn)
    elif backend == "mysql":
        table_name = str(request.mysql_config.get("table", "campaign_data"))
        dataframe = _read_mysql_table_as_dataframe_sqlalchemy(request.mysql_config, table_name)
        if dataframe is None:
            conn = get_mysql_connection(request.mysql_config)
            try:
                dataframe = _read_mysql_table_as_dataframe(conn, table_name)
            finally:
                conn.close()
    elif backend == "gcs":
        dataframe = _read_gcs_monthly_csvs_as_dataframe(
            gcs_bucket=request.gcs_bucket,
            gcs_prefix=request.gcs_prefix,
            gcs_credentials_json=request.gcs_credentials_json,
        )
    else:
        raise ValueError(f"Unsupported DB_BACKEND: {backend}. Use 'sqlite', 'mysql', or 'gcs'.")

    mapping = load_field_mapping(request.field_mapping_file)
    dataframe = apply_field_mapping(dataframe, mapping)

    _DF_CACHE["payload"] = dataframe
    _DF_CACHE["backend"] = backend
    _DF_CACHE["source_mtime_ns"] = source_mtime_ns
    _DF_CACHE["source_size"] = source_size
    _DF_CACHE["expires_at"] = now + max(request.cache_ttl_seconds, 1)
    return dataframe
