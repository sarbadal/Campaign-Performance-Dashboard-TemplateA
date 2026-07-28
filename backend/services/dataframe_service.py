from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Callable

import pandas as pd

from backend.services.data_sources import (
    read_gcs_monthly_csvs_as_dataframe,
    read_mysql_campaign_dataframe,
    read_sqlite_campaign_dataframe,
)
from backend.services.field_mapping_service import apply_field_mapping, load_field_mapping


_DF_CACHE: dict[str, object] = {
    "expires_at": 0.0,
    "backend": None,
    "source_mtime_ns": None,
    "source_size": None,
    "payload": None,
}


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


ReaderFunc = Callable[[DataframeRequest], pd.DataFrame]


# Mapping of database backends to their respective reader functions
# The reader functions are responsible for loading campaign data into a pandas 
# DataFrame from the specified backend.
READERS: dict[str, ReaderFunc] = {
    "sqlite": lambda request: read_sqlite_campaign_dataframe(request.sqlite_db_file),
    "mysql": lambda request: read_mysql_campaign_dataframe(request.mysql_config),
    "gcs": lambda request: read_gcs_monthly_csvs_as_dataframe(
        gcs_bucket=request.gcs_bucket,
        gcs_prefix=request.gcs_prefix,
        gcs_credentials_json=request.gcs_credentials_json,
    ),
}


def get_campaign_dataframe(request: DataframeRequest) -> pd.DataFrame:
    """
    Load campaign data into a reusable pandas DataFrame from configured DB backend.
    This function checks for a cached DataFrame and returns it if valid. If not, 
    it reads the data from the specified backend, applies field mapping, and caches the result.
    """
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

    reader = READERS.get(backend)
    if reader is None:
        supported = ", ".join(f"'{name}'" for name in sorted(READERS))
        raise ValueError(f"Unsupported DB_BACKEND: {backend}. Use {supported}.")

    dataframe = reader(request)

    mapping = load_field_mapping(request.field_mapping_file)
    dataframe = apply_field_mapping(dataframe, mapping)

    _DF_CACHE["payload"] = dataframe
    _DF_CACHE["backend"] = backend
    _DF_CACHE["source_mtime_ns"] = source_mtime_ns
    _DF_CACHE["source_size"] = source_size
    _DF_CACHE["expires_at"] = now + max(request.cache_ttl_seconds, 1)
    return dataframe
