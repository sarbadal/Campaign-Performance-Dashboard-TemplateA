from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd


def _connect_sqlite(db_file: Path) -> sqlite3.Connection:
    """
    Establish a connection to a SQLite database file, creating the file and 
    parent directories if they do not exist.
    """
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def read_sqlite_campaign_dataframe(sqlite_db_file: Path) -> pd.DataFrame:
    """Read campaign data from a SQLite database file into a pandas DataFrame."""
    with _connect_sqlite(sqlite_db_file) as conn:
        return pd.read_sql_query("SELECT * FROM campaign_data", conn)
