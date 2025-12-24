"""
MasterDB Database Connection Management

Provides connection management for SQLite database.
"""

import sqlite3
import os
from pathlib import Path

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "db" / "masterdb.sqlite"

# Global connection instance
_connection = None


def get_connection(db_path=None, create_if_missing=True):
    """
    Get a database connection.

    Args:
        db_path: Path to the database file. Uses default if not specified.
        create_if_missing: If True, creates the database if it doesn't exist.

    Returns:
        sqlite3.Connection object
    """
    global _connection

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    db_path = Path(db_path)

    # Create directory if needed
    if create_if_missing:
        db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create connection with foreign key support
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # Enable column access by name

    _connection = conn
    return conn


def close_connection():
    """Close the global connection if open."""
    global _connection
    if _connection:
        _connection.close()
        _connection = None


def get_db_path():
    """Get the default database path."""
    return DEFAULT_DB_PATH


def db_exists(db_path=None):
    """Check if the database file exists."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    return Path(db_path).exists()


def get_db_info(conn):
    """Get database information."""
    cursor = conn.cursor()

    # Get table list
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    # Get index count
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
    index_count = cursor.fetchone()[0]

    # Get database file size
    db_path = Path(conn.execute("PRAGMA database_list").fetchone()[2])
    file_size = db_path.stat().st_size if db_path.exists() else 0

    return {
        "tables": tables,
        "table_count": len(tables),
        "index_count": index_count,
        "file_size_bytes": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
    }


class DatabaseContext:
    """Context manager for database connections."""

    def __init__(self, db_path=None):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.conn = get_connection(self.db_path)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()
        return False
