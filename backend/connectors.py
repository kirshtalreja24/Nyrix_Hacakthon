"""
Connectors — CSV/DuckDB (Connector A) and PostgreSQL (Connector B).
Both normalize into the same DataFrame shape for downstream processing.
Cross-source queries via DuckDB postgres_scanner.
"""

import os
import io
import logging
from urllib.parse import quote_plus
import pandas as pd
import duckdb
import psycopg2
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("connectors")


# ─── Connector A: CSV → DuckDB (in-memory) ───────────────────────────────────

class CSVConnector:
    def __init__(self):
        self.conn = duckdb.connect(":memory:")
        self.tables = {}  # table_name -> DataFrame
        self._loaded = False

    def load_csv(self, file_content: bytes, filename: str) -> dict:
        """Load any CSV file into DuckDB and auto-clean the data."""
        raw_df = pd.read_csv(io.BytesIO(file_content))

        # Derive table name from filename (sanitize for SQL)
        table_name = os.path.splitext(filename)[0]
        table_name = table_name.replace(" ", "_").replace("-", "_")
        table_name = "".join(c for c in table_name if c.isalnum() or c == "_")
        if not table_name or table_name[0].isdigit():
            table_name = "uploaded_data"

        # Data cleaning
        cleaning_notes = []
        df = raw_df.copy()

        # Handle numeric columns — fill NaN, clamp negatives
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                na_count = df[col].isna().sum()
                neg_count = (df[col] < 0).sum()
                if na_count > 0:
                    df[col] = df[col].fillna(0)
                    cleaning_notes.append(f"Filled {na_count} null/NaN values in '{col}' with 0")
                if neg_count > 0:
                    df[col] = df[col].clip(lower=0)
                    cleaning_notes.append(f"Clamped {neg_count} negative values in '{col}' to 0")

        # Handle date columns
        for col in df.columns:
            col_lower = col.lower()
            if any(kw in col_lower for kw in ("date", "time", "_at", "week")):
                try:
                    df[col] = pd.to_datetime(df[col])
                except Exception:
                    pass

        # Handle string columns
        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]):
                df[col] = df[col].astype(str).str.strip().replace("nan", "")
                if df[col].isna().any():
                    df[col] = df[col].fillna("")

        # Auto-detect date columns among remaining string columns
        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
                sample = df[col].dropna().head(20)
                if len(sample) == 0:
                    continue
                date_like = sample.astype(str).str.match(
                    r'^\d{2,4}[/-]\d{1,2}[/-]\d{2,4}(\s\d{1,2}:\d{2})?$'
                ).sum()
                if date_like >= len(sample) * 0.5:
                    try:
                        df[col] = pd.to_datetime(df[col])
                    except Exception:
                        pass

        # Register in DuckDB
        self.conn.execute(f"DROP TABLE IF EXISTS \"{table_name}\"")
        self.conn.register(table_name, df)
        self.tables[table_name] = df
        self._loaded = True

        return {
            "table": table_name,
            "rows": len(df),
            "columns": list(df.columns),
            "cleaning": cleaning_notes if cleaning_notes else ["No cleaning needed"],
        }

    def attach_postgres(self, host: str, port: str, db: str, user: str, password: str) -> dict:
        """
        Attach a Postgres database into DuckDB via postgres_scanner extension.
        This enables cross-source queries joining CSV + Postgres data in a single SQL statement.
        """
        try:
            # Install and load the postgres_scanner extension
            self.conn.execute("INSTALL postgres; LOAD postgres;")

            # Build the connection string for DuckDB's postgres_scanner
            conn_str = f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{db}?sslmode=require"

            # ATTACH the Postgres database — tables become queryable as "pg_tablename"
            self.conn.execute(f"ATTACH '{conn_str}' AS pg (TYPE postgres)")

            log.info("Postgres attached to DuckDB via postgres_scanner: %s/%s", host, db)
            return {"attached": True}
        except Exception as e:
            log.warning("Failed to attach Postgres to DuckDB: %s", e)
            return {"attached": False, "error": str(e)}

    def detach_postgres(self):
        """Detach the Postgres database from DuckDB."""
        try:
            self.conn.execute("DETACH pg")
        except Exception:
            pass

    def clear(self):
        """Clear all loaded CSV data and reset DuckDB."""
        try:
            self.conn.close()
        except Exception:
            pass
        self.conn = duckdb.connect(":memory:")
        self.tables = {}
        self._loaded = False

    def query(self, sql: str) -> pd.DataFrame:
        """Execute SQL against the in-memory DuckDB."""
        result = self.conn.execute(sql).fetchdf()
        return result

    def status(self) -> dict:
        info = {"loaded": self._loaded, "connector": "csv_duckdb"}
        for name, df in self.tables.items():
            info[f"{name}_rows"] = len(df)
            info[f"{name}_columns"] = list(df.columns)
        return info

    def get_schema(self) -> str:
        """Return a SQL schema description for the LLM prompt."""
        if not self.tables:
            return "No data loaded."
        schema_parts = []
        for name, df in self.tables.items():
            types = []
            for col in df.columns:
                dtype = str(df[col].dtype)
                types.append(f"{col} ({dtype})")
            schema_parts.append(f"Table '{name}' columns: {types}")
        return "\n".join(schema_parts)


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
        self.tables = []

    def connect(self) -> dict:
        """Test and establish Postgres connection, discover all tables."""
        try:
            url = f"postgresql://{self.user}:{quote_plus(self.password)}@{self.host}:{self.port}/{self.db}?sslmode=require"
            self.engine = create_engine(url, pool_pre_ping=True)

            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
                    "ORDER BY table_name"
                ))
                self.tables = [row[0] for row in result]

            if not self.tables:
                return {
                    "connected": True,
                    "host": self.host,
                    "database": self.db,
                    "tables": [],
                    "warning": "Connected but no tables found in the database.",
                }

            table_info = {}
            with self.engine.connect() as conn:
                for table_name in self.tables:
                    try:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM \"{table_name}\""))
                        table_info[f"{table_name}_rows"] = result.scalar()
                    except Exception:
                        table_info[f"{table_name}_rows"] = 0

            self._connected = True
            return {
                "connected": True,
                "host": self.host,
                "database": self.db,
                "tables": self.tables,
                **table_info,
            }
        except Exception as e:
            self._connected = False
            return {"connected": False, "error": str(e)}

    def disconnect(self):
        """Disconnect from PostgreSQL."""
        if self.engine:
            try:
                self.engine.dispose()
            except Exception:
                pass
        self.engine = None
        self._connected = False
        self.tables = []

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
                    result = conn.execute(text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
                        "ORDER BY table_name"
                    ))
                    self.tables = [row[0] for row in result]

                    for table_name in self.tables:
                        try:
                            result = conn.execute(text(f"SELECT COUNT(*) FROM \"{table_name}\""))
                            info[f"{table_name}_rows"] = result.scalar()
                        except Exception:
                            info[f"{table_name}_rows"] = 0
            except Exception:
                info["connected"] = False
        return info

    def get_schema(self) -> str:
        """Return a SQL schema description for the LLM prompt."""
        if not self._connected:
            return "PostgreSQL not connected."
        schema_parts = []
        with self.engine.connect() as conn:
            for table_name in self.tables:
                result = conn.execute(text(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}' AND table_schema = 'public'
                    ORDER BY ordinal_position
                """))
                cols = [(r[0], r[1]) for r in result]
                schema_parts.append(f"Table '{table_name}' columns: {cols}")
        return "\n".join(schema_parts)


# ─── Unified wrapper ──────────────────────────────────────────────────────────

class UnifiedSource:
    """Wraps both connectors behind a single interface."""
    def __init__(self):
        self.csv = CSVConnector()
        self.postgres = PostgresConnector()
        self._postgres_attached = False

    def attach_postgres_for_cross_source(self):
        """Attach Postgres into DuckDB for cross-source queries."""
        if not self.postgres._connected:
            return {"attached": False, "error": "PostgreSQL not connected."}
        if self._postgres_attached:
            return {"attached": True}
        result = self.csv.attach_postgres(
            self.postgres.host, self.postgres.port,
            self.postgres.db, self.postgres.user, self.postgres.password
        )
        if result.get("attached"):
            self._postgres_attached = True
        return result

    def query_cross_source(self, sql: str) -> pd.DataFrame:
        """Execute a cross-source query against DuckDB with Postgres attached."""
        return self.csv.query(sql)

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

    def clear_csv(self):
        """Clear CSV data source."""
        self.csv.clear()
        return {"cleared": True}

    def disconnect_postgres(self):
        """Disconnect PostgreSQL."""
        self.postgres.disconnect()
        return {"disconnected": True}

    def status(self) -> dict:
        return {
            "csv": self.csv.status(),
            "postgres": self.postgres.status(),
        }
