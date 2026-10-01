"""CLI for the AI Home Digital Twin.

Usage:
    python -m twin.cli asset add --name "Furnace" --trade hvac ...
    python -m twin.cli warranty add --title "..." --expires-at 2028-01-01
    python -m twin.cli receipt add --title "..." --vendor "..." --amount 120
    python -m twin.cli maintenance log --task "Filter change" --performed-at 2026-09-01
    python -m twin.cli ask "warranties expiring soon"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .assets import AssetRegistry
from .maintenance import MaintenanceLog
from .query import TwinQuery
from .store import TwinStore


def _store(args) -> TwinStore:
    return TwinStore(args.db)


def _dump(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="twin", description="AI Home Digital Twin")
    p.add_argument("--db", default="twin.db", help="SQLite database path")
    sub = p.add_subparsers(dest="cmd", required=True)

    # asset ---------------------------------------------------------------
    pa = sub.add_parser("asset"); sa = pa.add_subparsers(dest="op", required=True)
    aa = sa.add_parser("add")
    aa.add_argument("--name", required=True)
    for f in ("category", "trade", "area", "brand", "model", "serial",
              "purchase-date", "vendor", "notes"):
        aa.add_argument("--" + f)
    aa.add_argument("--purchase-price", type=float)
    al = sa.add_parser("list")
    for f in ("category", "trade", "area", "search"):
        al.add_argument("--" + f)

    # warranty / receipt / photo / floor-plan --------------------------------
    for kind in ("warranty", "receipt", "photo", "floor-plan", "manual"):
        pk = sub.add_parser(kind); sk = pk.add_subparsers(dest="op", required=True)
        ak = sk.add_parser("add")
        ak.add_argument("--title", required=True)
        ak.add_argument("--file")
        ak.add_argument("--vendor")
        ak.add_argument("--amount", type=float)
        ak.add_argument("--doc-date")
        ak.add_argument("--expires-at")
        ak.add_argument("--asset-id", type=int)
        ak.add_argument("--notes")

    # maintenance ------------------------------------------------------------
    pm = sub.add_parser("maintenance"); sm = pm.add_subparsers(dest="op", required=True)
    ml = sm.add_parser("log")
    ml.add_argument("--task", required=True)
    ml.add_argument("--performed-at", required=True)
    ml.add_argument("--asset-id", type=int)
    ml.add_argument("--cost", type=float)
    ml.add_argument("--vendor")
    ml.add_argument("--next-due")
    ml.add_argument("--notes")
    sm.add_parser("due")

    # ask --------------------------------------------------------------------
    qa = sub.add_parser("ask")
    qa.add_argument("question", nargs="+")

    args = p.parse_args(argv)
    store = _store(args)
    assets = AssetRegistry(store)
    maint = MaintenanceLog(store)

    try:
        if args.cmd == "asset" and args.op == "add":
            _dump({"id": assets.add_asset(
                args.name,
                category=args.category or "appliance",
                trade=args.trade, area=args.area, brand=args.brand,
                model=args.model, serial=args.serial,
                purchase_date=args.purchase_date,
                purchase_price=args.purchase_price,
                vendor=args.vendor, notes=args.notes)})
        elif args.cmd == "asset" and args.op == "list":
            _dump(assets.list_assets(category=args.category, trade=args.trade,
                                     area=args.area, search=args.search))
        elif args.cmd in ("warranty", "receipt", "photo", "floor-plan", "manual") \
                and args.op == "add":
            kind = args.cmd.replace("-", "_")
            _dump({"id": assets.add_document(
                kind, args.title, asset_id=args.asset_id,
                file_path=args.file, vendor=args.vendor, amount=args.amount,
                doc_date=args.doc_date, expires_at=args.expires_at,
                notes=args.notes)})
        elif args.cmd == "maintenance" and args.op == "log":
            _dump({"id": maint.log(args.task, args.performed_at,
                                   asset_id=args.asset_id, cost=args.cost,
                                   vendor=args.vendor, next_due=args.next_due,
                                   notes=args.notes)})
        elif args.cmd == "maintenance" and args.op == "due":
            _dump(maint.due_soon())
        elif args.cmd == "ask":
            q = TwinQuery(store)
            out = q.run(" ".join(args.question))
            print(out["summary"])
            _dump(out["results"])
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
