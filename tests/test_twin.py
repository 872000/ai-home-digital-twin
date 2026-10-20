"""Smoke tests for the AI Home Digital Twin modules."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from twin.assets import AssetRegistry
from twin.maintenance import MaintenanceLog
from twin.query import TwinQuery
from twin.store import TwinStore


def fresh():
    store = TwinStore(":memory:")
    return store, AssetRegistry(store), MaintenanceLog(store), TwinQuery(store)


def test_assets_and_warranty_expiry():
    store, assets, maint, q = fresh()
    fid = assets.add_asset("Furnace", category="system", trade="hvac",
                           area="House / Basement", brand="Carrier")
    assets.add_document("warranty", "Furnace 10-year warranty", asset_id=fid,
                        expires_at="2026-11-15")
    assets.add_document("warranty", "Old dishwasher warranty", expires_at="2020-01-01")
    assets.add_document("receipt", "Plumbing invoice - sump pump",
                        vendor="ABC Plumbing", amount=450.0, doc_date="2024-03-10")
    assets.attach_photo("Kitchen after reno", "/photos/kitchen.jpg")
    assets.add_floor_plan("Ground floor plan", "/plans/ground.pdf",
                          area="House / Ground Floor")

    expiring = assets.warranties_expiring(within_days=90, today="2026-10-01")
    assert len(expiring) == 1 and expiring[0]["asset_name"] == "Furnace", expiring
    expired = assets.expired_warranties(today="2026-10-01")
    assert len(expired) == 1, expired
    assert len(assets.list_documents(kind="photo")) == 1
    assert len(assets.list_documents(kind="floor_plan")) == 1
    store.close()


def test_maintenance_log_and_due():
    store, assets, maint, q = fresh()
    fid = assets.add_asset("Furnace", category="system", trade="hvac")
    maint.log("Annual service", "2025-10-01", asset_id=fid, cost=180.0,
              vendor="ABC Heating", next_due="2026-10-15")
    maint.log("Filter change", "2026-06-01", asset_id=fid, cost=25.0,
              next_due="2026-12-01")
    due = maint.due_soon(within_days=60, today="2026-10-01")
    assert len(due) == 1 and due[0]["task"] == "Annual service", due
    assert maint.lifetime_cost(fid) == 205.0
    store.close()


def test_natural_language_queries():
    store, assets, maint, q = fresh()
    fid = assets.add_asset("Sump Pump", category="system", trade="plumbing")
    assets.add_document("receipt", "Sump pump install", asset_id=fid,
                        vendor="ABC Plumbing", amount=450.0, doc_date="2024-03-10")
    assets.add_document("warranty", "Sump pump warranty", asset_id=fid,
                        expires_at="2026-12-01")

    r = q.run("warranties expiring soon")
    assert r["plan"]["entity"] == "warranty" and len(r["results"]) == 1, r
    r = q.run("plumbing receipts 2024")
    assert r["plan"]["entity"] == "receipt" and r["plan"]["year"] == 2024, r
    assert len(r["results"]) == 1, r
    r = q.run("expired warranties")
    assert r["plan"]["window"] == "expired" and len(r["results"]) == 0, r
    store.close()


def test_total_spend_by_year():
    store, assets, maint, q = fresh()
    fid = assets.add_asset("Furnace", category="system", trade="hvac")
    maint.log("Annual service", "2025-10-01", asset_id=fid, cost=180.0)
    maint.log("Filter change", "2026-06-01", asset_id=fid, cost=25.0)
    assert maint.total_spend(year=2026) == 25.0
    assert maint.total_spend(year=2025) == 180.0
    assert maint.total_spend(year=2024) == 0.0
    assert maint.total_spend() == 205.0
    store.close()


if __name__ == "__main__":
    test_assets_and_warranty_expiry()
    test_maintenance_log_and_due()
    test_natural_language_queries()
    test_total_spend_by_year()
    print("all twin smoke tests passed")
