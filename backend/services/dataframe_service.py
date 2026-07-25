from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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


@dataclass
class DataframeRequest:
    db_backend: str
    sqlite_db_file: Path
    mysql_config: dict[str, object]
    field_mapping_file: Path
    cache_ttl_seconds: int = 300


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
    else:
        raise ValueError(f"Unsupported DB_BACKEND: {backend}. Use 'sqlite' or 'mysql'.")

    mapping = load_field_mapping(request.field_mapping_file)
    dataframe = apply_field_mapping(dataframe, mapping)

    _DF_CACHE["payload"] = dataframe
    _DF_CACHE["backend"] = backend
    _DF_CACHE["source_mtime_ns"] = source_mtime_ns
    _DF_CACHE["source_size"] = source_size
    _DF_CACHE["expires_at"] = now + max(request.cache_ttl_seconds, 1)
    return dataframe
