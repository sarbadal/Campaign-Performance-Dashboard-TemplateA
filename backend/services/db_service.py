from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


@dataclass
class DbSummary:
    total_spend: float
    total_impressions: int
    total_clicks: int
    total_conversions: int
    total_reach: int
    total_campaigns: int
    date_min: str | None
    date_max: str | None


def _connect(db_file: Path) -> sqlite3.Connection:
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def get_sqlite_connection(db_file: Path) -> sqlite3.Connection:
    """Public SQLite connection helper for shared data access modules."""
    return _connect(db_file)


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def ensure_sqlite_synced(csv_file: Path, db_file: Path) -> None:
    """Create/update SQLite table from CSV when source file changed."""
    stat = csv_file.stat()
    source_mtime_ns = int(stat.st_mtime_ns)
    source_size = int(stat.st_size)

    with _connect(db_file) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ingestion_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                source_mtime_ns INTEGER NOT NULL,
                source_size INTEGER NOT NULL,
                row_count INTEGER NOT NULL,
                ingested_at_utc TEXT NOT NULL
            )
            """
        )

        current = conn.execute(
            "SELECT source_mtime_ns, source_size FROM ingestion_state WHERE id = 1"
        ).fetchone()

        if current and int(current[0]) == source_mtime_ns and int(current[1]) == source_size:
            return

        with csv_file.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            headers = next(reader)
            if not headers:
                raise ValueError("CSV file has no headers")

            conn.execute("PRAGMA synchronous=OFF")
            conn.execute("DROP TABLE IF EXISTS campaign_data")

            columns_sql = ", ".join(f"{_quote_ident(col)} TEXT" for col in headers)
            conn.execute(f"CREATE TABLE campaign_data ({columns_sql})")

            placeholders = ", ".join("?" for _ in headers)
            insert_sql = f"INSERT INTO campaign_data VALUES ({placeholders})"

            row_count = 0
            batch: list[tuple[str, ...]] = []
            for row in reader:
                if len(row) < len(headers):
                    row = row + [""] * (len(headers) - len(row))
                elif len(row) > len(headers):
                    row = row[: len(headers)]

                batch.append(tuple(row))
                if len(batch) >= 5000:
                    conn.executemany(insert_sql, batch)
                    row_count += len(batch)
                    batch.clear()

            if batch:
                conn.executemany(insert_sql, batch)
                row_count += len(batch)

            if "DATE" in headers:
                conn.execute('CREATE INDEX IF NOT EXISTS idx_campaign_data_date ON campaign_data ("DATE")')
            if "CAMPAIGN_NAME" in headers:
                conn.execute(
                    'CREATE INDEX IF NOT EXISTS idx_campaign_data_campaign_name ON campaign_data ("CAMPAIGN_NAME")'
                )

            ingested_at = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO ingestion_state(id, source_mtime_ns, source_size, row_count, ingested_at_utc)
                VALUES(1, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source_mtime_ns=excluded.source_mtime_ns,
                    source_size=excluded.source_size,
                    row_count=excluded.row_count,
                    ingested_at_utc=excluded.ingested_at_utc
                """,
                (source_mtime_ns, source_size, row_count, ingested_at),
            )
            conn.commit()


def fetch_summary(db_file: Path) -> DbSummary:
    """Compute high-level KPI aggregates from SQLite."""
    with _connect(db_file) as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(COALESCE(CAST(NULLIF(REPLACE("AMOUNT_SPENT", ',', ''), '') AS REAL), 0)), 0) AS total_spend,
                COALESCE(SUM(COALESCE(CAST(NULLIF(REPLACE("IMPRESSIONS", ',', ''), '') AS REAL), 0)), 0) AS total_impressions,
                COALESCE(SUM(COALESCE(CAST(NULLIF(REPLACE("CLICKS", ',', ''), '') AS REAL), 0)), 0) AS total_clicks,
                COALESCE(SUM(COALESCE(CAST(NULLIF(REPLACE("CONVERSIONS", ',', ''), '') AS REAL), 0)), 0) AS total_conversions,
                COALESCE(SUM(COALESCE(CAST(NULLIF(REPLACE("REACH", ',', ''), '') AS REAL), 0)), 0) AS total_reach,
                COUNT(
                    DISTINCT CASE
                        WHEN TRIM(COALESCE("CAMPAIGN_NAME", '')) = '' THEN NULL
                        ELSE TRIM("CAMPAIGN_NAME")
                    END
                ) AS total_campaigns,
                MIN(NULLIF(TRIM(COALESCE("DATE", '')), '')) AS date_min,
                MAX(NULLIF(TRIM(COALESCE("DATE", '')), '')) AS date_max
            FROM campaign_data
            """
        ).fetchone()

    if row is None:
        return DbSummary(0.0, 0, 0, 0, 0, 0, None, None)

    return DbSummary(
        total_spend=float(row[0] or 0.0),
        total_impressions=int(round(float(row[1] or 0.0))),
        total_clicks=int(round(float(row[2] or 0.0))),
        total_conversions=int(round(float(row[3] or 0.0))),
        total_reach=int(round(float(row[4] or 0.0))),
        total_campaigns=int(row[5] or 0),
        date_min=row[6] if row[6] else None,
        date_max=row[7] if row[7] else None,
    )


def fetch_sqlite_last_ingested_at(db_file: Path) -> str | None:
    """Return latest ingestion timestamp from SQLite state table."""
    with _connect(db_file) as conn:
        row = conn.execute(
            "SELECT ingested_at_utc FROM ingestion_state WHERE id = 1"
        ).fetchone()

    if row is None or not row[0]:
        return None

    return str(row[0])
