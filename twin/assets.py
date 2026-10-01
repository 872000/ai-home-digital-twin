"""Asset + document registry for the AI Home Digital Twin.

Assets: appliances, fixtures, systems (HVAC, water heater...).
Documents: receipts, warranties (with expiry tracking), manuals,
floor plans, and photos — all by local file reference so nothing
ever leaves the machine.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from .store import TwinStore

VALID_ASSET_CATEGORIES = {"appliance", "fixture", "system", "vehicle", "other"}
VALID_DOC_KINDS = {"receipt", "warranty", "manual", "floor_plan", "photo", "other"}


def _row_to_dict(row) -> dict[str, Any]:
    return dict(row) if row is not None else None  # type: ignore[return-value]


class AssetRegistry:
    def __init__(self, store: TwinStore) -> None:
        self.store = store

    # ------------------------------------------------------------------ assets
    def add_asset(
        self,
        name: str,
        category: str = "appliance",
        trade: str | None = None,
        area: str | None = None,
        brand: str | None = None,
        model: str | None = None,
        serial: str | None = None,
        purchase_date: str | None = None,
        purchase_price: float | None = None,
        vendor: str | None = None,
        notes: str | None = None,
    ) -> int:
        if category not in VALID_ASSET_CATEGORIES:
            raise ValueError(f"unknown asset category: {category!r}")
        cur = self.store.conn.execute(
            """INSERT INTO assets
               (name, category, trade, area, brand, model, serial,
                purchase_date, purchase_price, vendor, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (name, category, trade, area, brand, model, serial,
             purchase_date, purchase_price, vendor, notes),
        )
        self.store.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_asset(self, asset_id: int) -> dict[str, Any] | None:
        row = self.store.conn.execute(
            "SELECT * FROM assets WHERE id=?", (asset_id,)
        ).fetchone()
        return _row_to_dict(row)

    def list_assets(
        self,
        category: str | None = None,
        trade: str | None = None,
        area: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        q = "SELECT * FROM assets WHERE 1=1"
        params: list[Any] = []
        if category:
            q += " AND category=?"; params.append(category)
        if trade:
            q += " AND trade LIKE ?"; params.append(f"%{trade}%")
        if area:
            q += " AND area LIKE ?"; params.append(f"%{area}%")
        if search:
            q += " AND (name LIKE ? OR brand LIKE ? OR model LIKE ? OR notes LIKE ?)"
            like = f"%{search}%"
            params.extend([like, like, like, like])
        q += " ORDER BY name"
        return [_row_to_dict(r) for r in self.store.conn.execute(q, params).fetchall()]

    def update_asset(self, asset_id: int, **fields: Any) -> None:
        allowed = {"name", "category", "trade", "area", "brand", "model",
                   "serial", "purchase_date", "purchase_price", "vendor", "notes"}
        sets = [f"{k}=?" for k in fields if k in allowed]
        if not sets:
            raise ValueError("no valid fields to update")
        self.store.conn.execute(
            f"UPDATE assets SET {', '.join(sets)} WHERE id=?",
            [fields[k] for k in fields if k in allowed] + [asset_id],
        )
        self.store.conn.commit()

    def delete_asset(self, asset_id: int) -> None:
        self.store.conn.execute("DELETE FROM assets WHERE id=?", (asset_id,))
        self.store.conn.commit()

    # --------------------------------------------------------------- documents
    def add_document(
        self,
        kind: str,
        title: str,
        asset_id: int | None = None,
        file_path: str | None = None,
        vendor: str | None = None,
        amount: float | None = None,
        doc_date: str | None = None,
        expires_at: str | None = None,
        notes: str | None = None,
    ) -> int:
        if kind not in VALID_DOC_KINDS:
            raise ValueError(f"unknown document kind: {kind!r}")
        cur = self.store.conn.execute(
            """INSERT INTO documents
               (kind, title, asset_id, file_path, vendor, amount,
                doc_date, expires_at, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (kind, title, asset_id, file_path, vendor, amount,
             doc_date, expires_at, notes),
        )
        self.store.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def list_documents(
        self,
        kind: str | None = None,
        asset_id: int | None = None,
        vendor: str | None = None,
        year: int | None = None,
    ) -> list[dict[str, Any]]:
        q = ("SELECT d.*, a.name AS asset_name FROM documents d "
             "LEFT JOIN assets a ON a.id=d.asset_id WHERE 1=1")
        params: list[Any] = []
        if kind:
            q += " AND d.kind=?"; params.append(kind)
        if asset_id:
            q += " AND d.asset_id=?"; params.append(asset_id)
        if vendor:
            q += " AND d.vendor LIKE ?"; params.append(f"%{vendor}%")
        if year:
            q += " AND substr(d.doc_date,1,4)=?"; params.append(str(year))
        q += " ORDER BY d.doc_date DESC"
        return [_row_to_dict(r) for r in self.store.conn.execute(q, params).fetchall()]

    def warranties_expiring(self, within_days: int = 90,
                            today: str | None = None) -> list[dict[str, Any]]:
        """Warranties expiring between today and today+within_days (inclusive)."""
        today = today or _dt.date.today().isoformat()
        horizon = (_dt.date.fromisoformat(today)
                   + _dt.timedelta(days=within_days)).isoformat()
        rows = self.store.conn.execute(
            """SELECT d.*, a.name AS asset_name FROM documents d
               LEFT JOIN assets a ON a.id=d.asset_id
               WHERE d.kind='warranty' AND d.expires_at IS NOT NULL
                 AND d.expires_at >= ? AND d.expires_at <= ?
               ORDER BY d.expires_at""",
            (today, horizon),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def expired_warranties(self, today: str | None = None) -> list[dict[str, Any]]:
        today = today or _dt.date.today().isoformat()
        rows = self.store.conn.execute(
            """SELECT d.*, a.name AS asset_name FROM documents d
               LEFT JOIN assets a ON a.id=d.asset_id
               WHERE d.kind='warranty' AND d.expires_at IS NOT NULL
                 AND d.expires_at < ?
               ORDER BY d.expires_at DESC""",
            (today,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def attach_photo(self, title: str, file_path: str,
                     asset_id: int | None = None,
                     area: str | None = None,
                     notes: str | None = None) -> int:
        """Register a photo by local file reference (optionally tied to an asset/area)."""
        return self.add_document("photo", title, asset_id=asset_id,
                                 file_path=file_path, notes=notes)

    def add_floor_plan(self, title: str, file_path: str,
                       area: str | None = None,
                       notes: str | None = None) -> int:
        """Register a floor plan by local file reference."""
        note = notes or ""
        if area:
            note = f"[area: {area}] {note}".strip()
        return self.add_document("floor_plan", title, file_path=file_path, notes=note)
