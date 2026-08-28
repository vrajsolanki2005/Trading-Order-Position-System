# Trading Order Position System

A production-grade Python system for ingesting high-throughput trading order updates, executing atomic idempotent balance updates, and tracking real-time net positions per symbol with persistent database storage.

## Features

- **Persistent State & Restart Recovery**: SQLite WAL-mode database backend stores both positions and processed event logs. Net positions and deduplication state survive service restarts.
- **Durable Idempotency & Atomic Updates**: Order deduplication and balance adjustments run in single atomic transactions (`BEGIN IMMEDIATE` with UPSERT), eliminating race conditions.
- **Audit Trail & On-demand Reconciliation**: Audit log of all accepted transactions with `GET /api/v1/reconcile` endpoint to verify database integrity against raw event history.
- **Observability & Probes**: Standardized `GET /health` (liveness probe), `GET /ready` (readiness probe verifying database connectivity), and `GET /position/{symbol}` for single-symbol queries.
- **Resilient Delivery**: Client incorporates rate limiting, exponential backoff with random jitter, and fail-fast handling for non-retryable 4xx client errors.

---

## Setup

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

---

## Running the Services

### 1. Start the Position Service

```bash
# Starts service with persistent SQLite database (defaults to trading_positions.db)
python -m src.position_service.main --host 127.0.0.1 --port 8000 --db-path trading_positions.db
```

### 2. Stream Order Updates

```bash
# Stream CSV rows at a specified rate (e.g. 50 events/sec)
python -m src.order_updater.main --csv-file sample_data/order_updates.csv --rate-limit 50
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/ready` | Readiness check (verifies database connection) |
| `GET` | `/position` | Snapshot of all symbol net positions |
| `GET` | `/position/{symbol}` | Get net position and last updated timestamp for a specific symbol |
| `POST` | `/events` | Ingest order event atomically (`BUY` / `SELL`) |
| `GET` | `/api/v1/reconcile` | Audit reconciliation between event history and stored positions |
| `POST` | `/reset` | Clear stored positions and event audit logs |

---

## Project Layout

```text
src/
  common/
    logger.py         # Formatted terminal logging
    models.py         # Pydantic schemas with strict validation
    rate_limiter.py   # Interval rate limiter
    validator.py      # CSV row parser and boundary validator
  order_updater/
    client.py         # HTTP client with exponential backoff & jitter
    main.py           # Streaming CLI orchestrator
    reader.py         # Memory-efficient CSV generator
  position_service/
    db.py             # SQLite database layer with atomic transactions & reconciliation
    main.py           # CLI entrypoint with configurable host/port/db
    server.py         # FastAPI service with health, ready & position endpoints
    tracker.py        # Domain position tracker wrapper
tests/
  test_e2e.py
  test_order_updater.py
  test_persistence.py # Restart recovery & reconciliation tests
  test_position_api.py
  test_tracker.py
  test_validator.py
```

---

## Running Tests

```bash
pytest -v
```