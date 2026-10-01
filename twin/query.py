"""Natural-language-ish retrieval over the home digital twin.

Not a real NLP engine — a pragmatic keyword + facet parser that turns
everyday phrasing into structured queries, e.g.:

    "warranties expiring soon"
    "expired warranties"
    "plumbing receipts 2024"
    "photos of the kitchen"
    "what maintenance is due soon"
    "how much did the furnace cost to maintain"

Facets understood: entity kind (warranty, receipt, photo, floor plan,
manual, asset, maintenance), trade (plumbing, electrical, hvac, ...),
year (4 digits), recency/expiry windows ("soon", "expired", "overdue"),
and free-text search over names, vendors, and notes.
"""

from __future__ import annotations

import re
from typing import Any

from .assets import AssetRegistry
from .maintenance import MaintenanceLog
from .store import TwinStore

TRADE_KEYWORDS = {
    "plumbing": "plumbing",
    "plumber": "plumbing",
    "electrical": "electrical",
    "electrician": "electrical",
    "hvac": "hvac",
    "heating": "hvac",
    "cooling": "hvac",
    "furnace": "hvac",
    "roofing": "roofing",
    "roof": "roofing",
    "carpentry": "carpentry",
    "painting": "painting",
    "landscaping": "landscaping",
    "appliance": "appliance",
}

ENTITY_KEYWORDS = {
    "warranty": "warranty", "warranties": "warranty",
    "receipt": "receipt", "receipts": "receipt",
    "invoice": "receipt", "invoices": "receipt",
    "photo": "photo", "photos": "photo",
    "picture": "photo", "pictures": "photo",
    "floor plan": "floor_plan", "floorplan": "floor_plan",
    "manual": "manual", "manuals": "manual",
    "asset": "asset", "assets": "asset",
    "appliance": "asset", "appliances": "asset",
    "maintenance": "maintenance", "service": "maintenance",
    "services": "maintenance", "repair": "maintenance",
    "repairs": "maintenance",
}


class TwinQuery:
    def __init__(self, store: TwinStore) -> None:
        self.store = store
        self.assets = AssetRegistry(store)
        self.maintenance = MaintenanceLog(store)

    # ---------------------------------------------------------------- parsing
    def parse(self, text: str) -> dict[str, Any]:
        t = text.lower()
        plan: dict[str, Any] = {
            "entity": None, "trade": None, "year": None,
            "window": None, "search": None, "raw": text,
        }

        for phrase, entity in sorted(ENTITY_KEYWORDS.items(), key=lambda kv: -len(kv[0])):
            if re.search(rf"\b{re.escape(phrase)}\b", t):
                plan["entity"] = entity
                t = re.sub(rf"\b{re.escape(phrase)}\b", " ", t)
                break

        for kw, trade in TRADE_KEYWORDS.items():
            if re.search(rf"\b{re.escape(kw)}\b", t):
                plan["trade"] = trade
                t = re.sub(rf"\b{re.escape(kw)}\b", " ", t)
                break

        m = re.search(r"\b(19|20)\d{2}\b", t)
        if m:
            plan["year"] = int(m.group(0))
            t = t.replace(m.group(0), " ")

        if re.search(r"\bexpir\w*\s+soon\b", text.lower()) or "expiring soon" in text.lower():
            plan["window"] = "expiring_soon"
            t = re.sub(r"\bexpir\w*\s+soon\b", " ", t)
        elif "expired" in text.lower():
            plan["window"] = "expired"
            t = re.sub(r"\bexpired\b", " ", t)
        elif re.search(r"\bdue\s+soon\b", text.lower()):
            plan["window"] = "due_soon"
            t = re.sub(r"\bdue\s+soon\b", " ", t)
        elif "overdue" in text.lower():
            plan["window"] = "overdue"
            t = re.sub(r"\boverdue\b", " ", t)

        leftover = re.sub(r"\b(what|which|show|me|the|of|for|in|on|is|are|my|all|any|list|find|get)\b",
                          " ", t)
        leftover = re.sub(r"\s+", " ", leftover).strip(" ?.,")
        plan["search"] = leftover or None
        return plan

    # ---------------------------------------------------------------- running
    def run(self, text: str) -> dict[str, Any]:
        """Run a natural-language query; returns {plan, results, summary}."""
        plan = self.parse(text)
        entity = plan["entity"] or "asset"
        results: list[dict[str, Any]] = []

        if entity == "warranty":
            if plan["window"] == "expired":
                results = self.assets.expired_warranties()
            else:
                results = self.assets.warranties_expiring()
            if plan["year"]:
                results = [r for r in results
                           if (r.get("expires_at") or "").startswith(str(plan["year"]))]
        elif entity == "receipt":
            results = self.assets.list_documents(
                kind="receipt", year=plan["year"])
        elif entity == "photo":
            results = self.assets.list_documents(kind="photo")
        elif entity == "floor_plan":
            results = self.assets.list_documents(kind="floor_plan")
        elif entity == "manual":
            results = self.assets.list_documents(kind="manual")
        elif entity == "maintenance":
            if plan["window"] in ("due_soon", "overdue"):
                results = self.maintenance.due_soon()
            else:
                results = self.maintenance.history()
            if plan["year"]:
                results = [r for r in results
                           if (r.get("performed_at") or "").startswith(str(plan["year"]))]
        else:  # assets
            results = self.assets.list_assets(
                trade=plan["trade"], search=plan["search"])

        # cross-cutting text filter for document entities
        if plan["search"] and entity in {"receipt", "photo", "floor_plan", "manual"}:
            s = plan["search"].lower()
            results = [r for r in results
                       if s in (r.get("title") or "").lower()
                       or s in (r.get("vendor") or "").lower()
                       or s in (r.get("notes") or "").lower()
                       or s in (r.get("asset_name") or "").lower()]

        return {"plan": plan, "results": results,
                "summary": self._summarize(plan, results)}

    _PLURALS = {"warranty": "warranties", "maintenance": "maintenance jobs"}

    @classmethod
    def _summarize(cls, plan: dict[str, Any], results: list[dict]) -> str:
        n = len(results)
        entity = plan["entity"] or "asset"
        plural = cls._PLURALS.get(entity, entity + "s")
        bits = [f"{n} {entity if n == 1 else plural}"]
        if plan["trade"]:
            bits.append(f"trade={plan['trade']}")
        if plan["year"]:
            bits.append(f"year={plan['year']}")
        if plan["window"]:
            bits.append(plan["window"].replace("_", " "))
        if plan["search"]:
            bits.append(f"matching '{plan['search']}'")
        return "Found " + ", ".join(bits) + "."
