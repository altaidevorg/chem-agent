# src/database/manager.py
import os
import duckdb
from typing import Optional
from contextlib import contextmanager
from .schemas import INITIAL_SCHEMA

class DatabaseManager:
    """
    Manages DuckDB connections with concurrency control and schema management.
    Ensures safe read/write operations and atomic updates.
    """

    def __init__(self, db_path: str = "data/chem_knowledge.db"):
        self.db_path = db_path
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    @contextmanager
    def get_connection(self, read_only: bool = True):
        """
        Provides a DuckDB connection context.
        query tools should use read_only=True.
        update tools should use read_only=False.
        """
        conn = duckdb.connect(self.db_path, read_only=read_only)
        try:
            yield conn
        finally:
            conn.close()

    def initialize_database(self):
        """Initializes the schema if the database is new or missing tables."""
        with self.get_connection(read_only=False) as conn:
            for statement in INITIAL_SCHEMA:
                conn.execute(statement)
            
            # Set initial version if not exists
            conn.execute("INSERT OR IGNORE INTO schema_version (version, description) VALUES (1, 'Initial Normalized Schema')")

    def atomic_swap(self, staging_table: str, main_table: str):
        """
        Safely swaps a staging table into the main table within a transaction.
        Prevents half-written data on API failures.
        """
        with self.get_connection(read_only=False) as conn:
            conn.execute("BEGIN TRANSACTION")
            try:
                # 1. Validation check (e.g., staging not empty)
                count = conn.execute(f"SELECT COUNT(*) FROM {staging_table}").fetchone()[0]
                if count == 0:
                    raise ValueError(f"Staging table {staging_table} is empty. Aborting swap.")

                # 2. Perform swap
                conn.execute(f"DELETE FROM {main_table}")
                conn.execute(f"INSERT INTO {main_table} SELECT * FROM {staging_table}")
                
                # 3. Cleanup
                conn.execute(f"DROP TABLE {staging_table}")
                
                conn.execute("COMMIT")
                return True
            except Exception as e:
                conn.execute("ROLLBACK")
                raise e

    def log_audit(self, source: str, event_type: str, records: int, status: str, error: Optional[str] = None):
        """Logs regulatory update events to the audit log."""
        with self.get_connection(read_only=False) as conn:
            conn.execute(
                "INSERT INTO regulatory_audit_log (source, event_type, records_changed, status, error_message) VALUES (?, ?, ?, ?, ?)",
                (source, event_type, records, status, error)
            )

    def reset_database(self):
        """
        Deletes the existing database file and re-initializes it with a clean schema.
        Use only during development or recovery.
        """
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.initialize_database()
