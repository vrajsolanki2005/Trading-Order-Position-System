# Trading Order Position System

This project reads CSV order updates, validates each row, and sends accepted events to a small API that tracks the net position for each symbol.

## Setup

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

## Start the service

```bash
python -m src.position_service.main --host 127.0.0.1 --port 8000
```

## Send orders

```bash
python -m src.order_updater.main --csv-file sample_data/order_updates.csv --rate-limit 50
```

## Rules

- BUY increases the position for a symbol.
- SELL decreases it.
- Duplicate `event_id` values are ignored after the first accepted event.
- Invalid rows are rejected before they reach the API.

## Project layout

```text
src/
  common/
    logger.py
    models.py
    rate_limiter.py
    validator.py
  order_updater/
    client.py
    main.py
    reader.py
  position_service/
    main.py
    server.py
    tracker.py
```

## Tests

```bash
pytest -q
```