from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from backend.services.db_service import DbSummary


def _quote_ident(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def _connect_mysql(mysql_config: dict[str, object]):
    try:
        import pymysql
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "MySQL backend selected but PyMySQL is not installed. Install requirements first."
        ) from exc

    return pymysql.connect(
        host=str(mysql_config.get("host", "127.0.0.1")),
        port=int(mysql_config.get("port", 3306)),
        user=str(mysql_config.get("user", "root")),
        password=str(mysql_config.get("password", "")),
        database=str(mysql_config.get("database", "campaign_performance")),
        charset="utf8mb4",
        autocommit=False,
    )


def get_mysql_connection(mysql_config: dict[str, object]):
    """Public MySQL connection helper for shared data access modules."""
    return _connect_mysql(mysql_config)


def ensure_mysql_synced(csv_file: Path, mysql_config: dict[str, object]) -> None:
    """Create/update MySQL table from CSV when source file changed."""
    table = str(mysql_config.get("table", "campaign_data"))
    state_table = str(mysql_config.get("state_table", "ingestion_state"))

    stat = csv_file.stat()
    source_mtime_ns = int(stat.st_mtime_ns)
    source_size = int(stat.st_size)

    conn = _connect_mysql(mysql_config)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {_quote_ident(state_table)} (
                    id TINYINT PRIMARY KEY,
                    source_mtime_ns BIGINT NOT NULL,
                    source_size BIGINT NOT NULL,
                    row_count BIGINT NOT NULL,
                    ingested_at_utc VARCHAR(64) NOT NULL
                )
                """
            )

            cur.execute(
                f"SELECT source_mtime_ns, source_size FROM {_quote_ident(state_table)} WHERE id = 1"
            )
            current = cur.fetchone()
            if current and int(current[0]) == source_mtime_ns and int(current[1]) == source_size:
                conn.commit()
                return

            with csv_file.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                headers = next(reader)
                if not headers:
                    raise ValueError("CSV file has no headers")

                cur.execute(f"DROP TABLE IF EXISTS {_quote_ident(table)}")
                columns_sql = ", ".join(f"{_quote_ident(col)} LONGTEXT NULL" for col in headers)
                cur.execute(f"CREATE TABLE {_quote_ident(table)} ({columns_sql})")

                placeholders = ", ".join(["%s"] * len(headers))
                insert_sql = f"INSERT INTO {_quote_ident(table)} VALUES ({placeholders})"

                row_count = 0
                batch: list[tuple[str, ...]] = []
                for row in reader:
                    if len(row) < len(headers):
                        row = row + [""] * (len(headers) - len(row))
                    elif len(row) > len(headers):
                        row = row[: len(headers)]

                    batch.append(tuple(row))
                    if len(batch) >= 5000:
                        cur.executemany(insert_sql, batch)
                        row_count += len(batch)
                        batch.clear()

                if batch:
                    cur.executemany(insert_sql, batch)
                    row_count += len(batch)

                ingested_at = datetime.now(timezone.utc).isoformat()
                cur.execute(
                    f"""
                    INSERT INTO {_quote_ident(state_table)}
                        (id, source_mtime_ns, source_size, row_count, ingested_at_utc)
                    VALUES (1, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        source_mtime_ns=VALUES(source_mtime_ns),
                        source_size=VALUES(source_size),
                        row_count=VALUES(row_count),
                        ingested_at_utc=VALUES(ingested_at_utc)
                    """,
                    (source_mtime_ns, source_size, row_count, ingested_at),
                )

        conn.commit()
    finally:
        conn.close()


def fetch_mysql_summary(mysql_config: dict[str, object]) -> DbSummary:
    """Compute high-level KPI aggregates from MySQL."""
    table = str(mysql_config.get("table", "campaign_data"))
    conn = _connect_mysql(mysql_config)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    COALESCE(SUM(COALESCE(CAST(NULLIF(REPLACE({_quote_ident('AMOUNT_SPENT')}, ',', ''), '') AS DECIMAL(20,6)), 0)), 0) AS total_spend,
                    COALESCE(SUM(COALESCE(CAST(NULLIF(REPLACE({_quote_ident('IMPRESSIONS')}, ',', ''), '') AS DECIMAL(20,6)), 0)), 0) AS total_impressions,
                    COALESCE(SUM(COALESCE(CAST(NULLIF(REPLACE({_quote_ident('CLICKS')}, ',', ''), '') AS DECIMAL(20,6)), 0)), 0) AS total_clicks,
                    COALESCE(SUM(COALESCE(CAST(NULLIF(REPLACE({_quote_ident('CONVERSIONS')}, ',', ''), '') AS DECIMAL(20,6)), 0)), 0) AS total_conversions,
                    COALESCE(SUM(COALESCE(CAST(NULLIF(REPLACE({_quote_ident('REACH')}, ',', ''), '') AS DECIMAL(20,6)), 0)), 0) AS total_reach,
                    COUNT(DISTINCT CASE
                        WHEN TRIM(COALESCE({_quote_ident('CAMPAIGN_NAME')}, '')) = '' THEN NULL
                        ELSE TRIM({_quote_ident('CAMPAIGN_NAME')})
                    END) AS total_campaigns,
                    MIN(NULLIF(TRIM(COALESCE({_quote_ident('DATE')}, '')), '')) AS date_min,
                    MAX(NULLIF(TRIM(COALESCE({_quote_ident('DATE')}, '')), '')) AS date_max
                FROM {_quote_ident(table)}
                """
            )
            row = cur.fetchone()
    finally:
        conn.close()

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
