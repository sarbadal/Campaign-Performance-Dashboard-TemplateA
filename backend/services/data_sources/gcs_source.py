from __future__ import annotations

from io import BytesIO
import json
import re

import pandas as pd


def _build_gcs_client(gcs_credentials_json: str | None):
    """Build a Google Cloud Storage client using the provided credentials JSON string."""
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
    """Extract a (year, month) tuple from the filename if it matches expected patterns."""
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


def read_gcs_monthly_csvs_as_dataframe(gcs_bucket: str, gcs_prefix: str, gcs_credentials_json: str | None) -> pd.DataFrame:
    """Read monthly CSV files from a GCS bucket and return a concatenated pandas DataFrame."""
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

        if list_prefix and blob_name.startswith(list_prefix):
            relative_name = blob_name[len(list_prefix):]
        else:
            relative_name = blob_name

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
