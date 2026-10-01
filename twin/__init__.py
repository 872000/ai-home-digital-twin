"""AI Home Digital Twin — companion layer for Cornerstone.

A local-first asset/document registry, maintenance log, and
natural-language-ish retrieval engine for everything about your home:
appliances, receipts, warranties, floor plans, photos, and service history.

Everything is stored in a single SQLite database (default: ./twin.db).
No network, no cloud, no telemetry.
"""

from .assets import AssetRegistry
from .maintenance import MaintenanceLog
from .query import TwinQuery
from .store import TwinStore, DEFAULT_DB_PATH

__all__ = [
    "AssetRegistry",
    "MaintenanceLog",
    "TwinQuery",
    "TwinStore",
    "DEFAULT_DB_PATH",
]

__version__ = "0.1.0"
