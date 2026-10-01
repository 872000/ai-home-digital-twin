"""Maintenance log for the AI Home Digital Twin.

Every service event on an asset: date, task, cost, vendor, and the
next scheduled service date. Powers "what's due soon" reminders and
per-asset lifetime cost rollups.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from .store import TwinStore


def _row_to_dict(row) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class MaintenanceLog:
    def __init__(self, store: TwinStore) -> None:
        self.store = store

    def log(
        self,
        task: str,
        performed_at: str,
        asset_id: int | None = None,
        cost: float | None = None,
        vendor: str | None = None,
        next_due: str | None = None,
        notes: str | None = None,
    ) -> int:
        cur = self.store.conn.execute(
            """INSERT INTO maintenance
               (asset_id, task, performed_at, cost, vendor, next_due, notes)
               VALUES (?,?,?,?,?,?,?)""",
            (asset_id, task, performed_at, cost, vendor, next_due, notes),
        )
        self.store.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def history(self, asset_id: int | None = None,
                limit: int = 100) -> list[dict[str, Any]]:
        q = ("SELECT m.*, a.name AS asset_name FROM maintenance m "
             "LEFT JOIN assets a ON a.id=m.asset_id")
        params: list[Any] = []
        if asset_id is not None:
            q += " WHERE m.asset_id=?"
            params.append(asset_id)
        q += " ORDER BY m.performed_at DESC LIMIT ?"
        params.append(limit)
        rows = self.store.conn.execute(q, params).fetchall()
        return [_row_to_dict(r) for r in rows]  # type: ignore[misc]

    def due_soon(self, within_days: int = 60,
                 today: str | None = None) -> list[dict[str, Any]]:
        """Recurring services whose next_due falls within the window (incl. overdue)."""
        today = today or _dt.date.today().isoformat()
        horizon = (_dt.date.fromisoformat(today)
                   + _dt.timedelta(days=within_days)).isoformat()
        rows = self.store.conn.execute(
            """SELECT m.*, a.name AS asset_name FROM maintenance m
               LEFT JOIN assets a ON a.id=m.asset_id
               WHERE m.next_due IS NOT NULL AND m.next_due <= ?
               ORDER BY m.next_due""",
            (horizon,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]  # type: ignore[misc]

    def lifetime_cost(self, asset_id: int) -> float:
        row = self.store.conn.execute(
            "SELECT COALESCE(SUM(cost),0) AS total FROM maintenance WHERE asset_id=?",
            (asset_id,),
        ).fetchone()
        return float(row["total"])

    def total_spend(self, year: int | None = None) -> float:
        q = "SELECT COALESCE(SUM(cost),0) AS total FROM maintenance WHERE 1=1"
        params: list[Any] = []
        if year:
            q += " AND substr(performed_at,1,4)=?"
            params.append(str(year))
        return float(self.store.conn.execute(q, params).fetchone()["total"])
