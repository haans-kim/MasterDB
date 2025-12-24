"""
MasterDB Database Module

SQLite database management for the MasterDB ontology-based survey question system.
"""

from .schema import create_all_tables, SCHEMA_VERSION
from .connection import get_connection, close_connection

__all__ = [
    'create_all_tables',
    'SCHEMA_VERSION',
    'get_connection',
    'close_connection',
]
