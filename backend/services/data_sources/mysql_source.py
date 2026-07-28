from __future__ import annotations

from urllib.parse import quote_plus

import pandas as pd


def _quote_mysql_ident(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def _connect_mysql(mysql_config: dict[str, object]):
    """Establish a connection to a MySQL database using the provided configuration dictionary."""
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


def _read_mysql_table_as_dataframe(conn, table_name: str) -> pd.DataFrame:
    """Read a MySQL table into a pandas DataFrame using a raw connection."""
    sql = f"SELECT * FROM {_quote_mysql_ident(table_name)}"
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        description = cur.description or []

    columns = [str(col[0]) for col in description]
    return pd.DataFrame(rows, columns=columns)


def _read_mysql_table_as_dataframe_sqlalchemy(mysql_config: dict[str, object], table_name: str) -> pd.DataFrame | None:
    """Read a MySQL table into a pandas DataFrame using SQLAlchemy if available."""
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


def read_mysql_campaign_dataframe(mysql_config: dict[str, object]) -> pd.DataFrame:
    """Read campaign data from a MySQL database into a pandas DataFrame."""
    table_name = str(mysql_config.get("table", "campaign_data"))
    dataframe = _read_mysql_table_as_dataframe_sqlalchemy(mysql_config, table_name)
    if dataframe is not None:
        return dataframe

    conn = _connect_mysql(mysql_config)
    try:
        return _read_mysql_table_as_dataframe(conn, table_name)
    finally:
        conn.close()
