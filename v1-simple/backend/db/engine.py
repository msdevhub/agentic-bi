"""DuckDB 引擎管理"""
import duckdb
from pathlib import Path
from .sample_data import generate

_conn: duckdb.DuckDBPyConnection | None = None

DB_PATH = Path(__file__).parent / "data.duckdb"


def get_connection() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        if not DB_PATH.exists():
            generate()
        _conn = duckdb.connect(str(DB_PATH), read_only=True)
        _print_info(_conn)
    return _conn


def _print_info(conn: duckdb.DuckDBPyConnection):
    tables = conn.execute("SHOW TABLES").fetchall()
    for (t,) in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"✅ 已加载表 {t}: {count} 条记录")


def execute_sql(sql: str) -> dict:
    conn = get_connection()
    try:
        result = conn.execute(sql)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        data = []
        for row in rows:
            record = {}
            for col, val in zip(columns, row):
                if hasattr(val, 'isoformat'):
                    record[col] = val.isoformat()
                elif hasattr(val, 'item'):
                    record[col] = val.item()
                else:
                    record[col] = val
            data.append(record)
        return {"success": True, "columns": columns, "data": data, "row_count": len(data)}
    except Exception as e:
        return {"success": False, "error": str(e), "columns": [], "data": [], "row_count": 0}


def get_schema_info() -> list[dict]:
    conn = get_connection()
    tables = conn.execute("SHOW TABLES").fetchall()
    schema = []
    for (table_name,) in tables:
        cols = conn.execute(f"DESCRIBE {table_name}").fetchall()
        schema.append({
            "table": table_name,
            "columns": [{"name": c[0], "type": c[1]} for c in cols],
        })
    return schema
