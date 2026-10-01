# Changelog — AI Home Digital Twin

All notable changes to the Digital Twin evolution of Cornerstone are documented here.

## [0.1.0] — 2026-10-01

### Added
- New `twin/` Python package: local-first AI Home Digital Twin companion layer
  (SQLite-backed, no network, no telemetry).
- `twin/store.py` — SQLite schema (assets, documents, maintenance) with
  `PRAGMA user_version` migrations.
- `twin/assets.py` — `AssetRegistry`: asset CRUD (appliance/fixture/system),
  document registry (receipt, warranty, manual, floor_plan, photo) by local
  file reference, warranty expiry tracking (`warranties_expiring`,
  `expired_warranties`), photo/floor-plan helpers.
- `twin/maintenance.py` — `MaintenanceLog`: service-event log with date, task,
  cost, vendor, next-due; `due_soon` reminders and `lifetime_cost` /
  `total_spend` rollups.
- `twin/query.py` — `TwinQuery`: natural-language-ish retrieval — keyword +
  faceted parser (entity, trade, year, expiry/due windows, free text), e.g.
  "warranties expiring soon", "plumbing receipts 2024".
- `twin/cli.py` — CLI (`asset`, `warranty`, `receipt`, `photo`, `floor-plan`,
  `manual`, `maintenance`, `ask`).
- `tests/test_twin.py` — smoke tests covering registry, expiry, maintenance
  due dates, and NL queries.
- README: "AI Home Digital Twin" section documenting the new layer.

### Changed
- Based on steilerDev/cornerstone @ `24ddfc9` (depth-1 snapshot); no upstream
  files modified except README.md.
