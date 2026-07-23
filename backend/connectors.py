"""
Connectors — CSV/DuckDB (Connector A) and PostgreSQL (Connector B).
Both normalize into the same DataFrame shape for downstream processing.
"""

import os
import io
import pandas as pd
import duckdb
import psycopg2
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


# ─── Connector A: CSV → DuckDB (in-memory) ───────────────────────────────────

class CSVConnector:
    def __init__(self):
        self.conn = duckdb.connect(":memory:")
        self.orders_df = None
        self.footfall_df = None
        self._loaded = False

    def load_csv(self, file_content: bytes, filename: str) -> dict:
        """Load a CSV file into DuckDB and store the DataFrame."""
        df = pd.read_csv(io.BytesIO(file_content))

        if filename.lower().startswith("orders"):
            table_name = "orders"
            self.orders_df = df
        elif filename.lower().startswith("footfall"):
            table_name = "footfall"
            self.footfall_df = df
        else:
            return {"error": f"Unrecognized file: {filename}. Expected 'orders' or 'footfall' CSV."}

        self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        self.conn.register(table_name, df)
        self._loaded = True

        return {
            "table": table_name,
            "rows": len(df),
            "columns": list(df.columns),
        }

    def query(self, sql: str) -> pd.DataFrame:
        """Execute SQL against the in-memory DuckDB."""
        result = self.conn.execute(sql).fetchdf()
        return result

    def status(self) -> dict:
        info = {"loaded": self._loaded, "connector": "csv_duckdb"}
        if self.orders_df is not None:
            info["orders_rows"] = len(self.orders_df)
            info["orders_columns"] = list(self.orders_df.columns)
        if self.footfall_df is not None:
            info["footfall_rows"] = len(self.footfall_df)
        return info

    def get_schema(self) -> str:
        """Return a SQL schema description for the LLM prompt."""
        schema_parts = []
        if self.orders_df is not None:
            schema_parts.append(f"Table 'orders' columns: {list(self.orders_df.columns)}")
        if self.footfall_df is not None:
            schema_parts.append(f"Table 'footfall' columns: {list(self.footfall_df.columns)}")
        return "\n".join(schema_parts) if schema_parts else "No data loaded."


# ─── Connector B: PostgreSQL (live database) ─────────────────────────────────

class PostgresConnector:
    def __init__(self):
        self.engine = None
        self._connected = False
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = os.getenv("POSTGRES_PORT", "5432")
        self.db = os.getenv("POSTGRES_DB", "business_analytics")
        self.user = os.getenv("POSTGRES_USER", "postgres")
        self.password = os.getenv("POSTGRES_PASSWORD", "")

    def connect(self) -> dict:
        """Test and establish Postgres connection."""
        try:
            url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
            self.engine = create_engine(url, pool_pre_ping=True)

            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM orders"))
                orders_count = result.scalar()
                result = conn.execute(text("SELECT COUNT(*) FROM footfall"))
                footfall_count = result.scalar()

            self._connected = True
            return {
                "connected": True,
                "host": self.host,
                "database": self.db,
                "orders_rows": orders_count,
                "footfall_rows": footfall_count,
            }
        except Exception as e:
            self._connected = False
            return {"connected": False, "error": str(e)}

    def query(self, sql: str) -> pd.DataFrame:
        """Execute SQL against PostgreSQL."""
        if not self._connected:
            raise RuntimeError("PostgreSQL not connected. Call connect() first.")
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
        return df

    def status(self) -> dict:
        info = {"connected": self._connected, "connector": "postgresql"}
        if self._connected:
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM orders"))
                    info["orders_rows"] = result.scalar()
                    result = conn.execute(text("SELECT COUNT(*) FROM footfall"))
                    info["footfall_rows"] = result.scalar()
            except Exception:
                info["connected"] = False
        return info

    def get_schema(self) -> str:
        """Return a SQL schema description for the LLM prompt."""
        if not self._connected:
            return "PostgreSQL not connected."
        schema_parts = []
        for table in ["orders", "footfall"]:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """))
                cols = [(r[0], r[1]) for r in result]
                schema_parts.append(f"Table '{table}' columns: {cols}")
        return "\n".join(schema_parts)


# ─── Unified wrapper ──────────────────────────────────────────────────────────

class UnifiedSource:
    """Wraps both connectors behind a single interface."""
    def __init__(self):
        self.csv = CSVConnector()
        self.postgres = PostgresConnector()

    def get_active_connector(self):
        """Return whichever connector is available, preferring CSV if both loaded."""
        if self.csv._loaded:
            return self.csv, "csv_duckdb"
        if self.postgres._connected:
            return self.postgres, "postgresql"
        return None, None

    def get_schema(self) -> str:
        parts = []
        if self.csv._loaded:
            parts.append(f"[CSV/DuckDB]\n{self.csv.get_schema()}")
        if self.postgres._connected:
            parts.append(f"[PostgreSQL]\n{self.postgres.get_schema()}")
        return "\n\n".join(parts) if parts else "No data sources connected."

    def status(self) -> dict:
        return {
            "csv": self.csv.status(),
            "postgres": self.postgres.status(),
        }
