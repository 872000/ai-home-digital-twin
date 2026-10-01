"""SQLite store for the AI Home Digital Twin.

Single-file, local-first persistence. Schema is versioned with
``PRAGMA user_version``; the store applies migrations on open.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(os.environ.get("TWIN_DB_PATH", "twin.db"))

SCHEMA_VERSION = 1

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS assets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    category      TEXT NOT NULL DEFAULT 'appliance',   -- appliance|fixture|system|vehicle|other
    trade         TEXT,                                 -- plumbing|electrical|hvac|...
    area          TEXT,                                 -- e.g. "House / Ground Floor / Kitchen"
    brand         TEXT,
    model         TEXT,
    serial        TEXT,
    purchase_date TEXT,                                 -- ISO YYYY-MM-DD
    purchase_price REAL,
    vendor        TEXT,
    notes         TEXT,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT NOT NULL,              -- receipt|warranty|manual|floor_plan|photo|other
    title       TEXT NOT NULL,
    asset_id    INTEGER REFERENCES assets(id) ON DELETE SET NULL,
    file_path   TEXT,                       -- local file reference (photo, scan, floor plan)
    vendor      TEXT,
    amount      REAL,
    doc_date    TEXT,                       -- ISO YYYY-MM-DD (purchase/receipt date)
    expires_at  TEXT,                       -- ISO YYYY-MM-DD (warranty expiry)
    notes       TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS maintenance (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id    INTEGER REFERENCES assets(id) ON DELETE SET NULL,
    task        TEXT NOT NULL,
    performed_at TEXT NOT NULL,             -- ISO YYYY-MM-DD
    cost        REAL,
    vendor      TEXT,
    next_due    TEXT,                       -- ISO YYYY-MM-DD (recurring service)
    notes       TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_documents_kind ON documents(kind);
CREATE INDEX IF NOT EXISTS idx_documents_asset ON documents(asset_id);
CREATE INDEX IF NOT EXISTS idx_documents_expires ON documents(expires_at);
CREATE INDEX IF NOT EXISTS idx_maintenance_asset ON maintenance(asset_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_due ON maintenance(next_due);
CREATE INDEX IF NOT EXISTS idx_assets_trade ON assets(trade);
CREATE INDEX IF NOT EXISTS idx_assets_area ON assets(area);
"""


class TwinStore:
    """Opens (and migrates) the twin SQLite database."""

    def __init__(self, path: str | os.PathLike | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_DB_PATH
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self) -> None:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version < SCHEMA_VERSION:
            self.conn.executescript(_SCHEMA)
            self.conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "TwinStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
