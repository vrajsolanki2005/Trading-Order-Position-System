from pathlib import Path
from typing import Any

from src.common.models import OrderEvent
from src.position_service.db import Database


class PositionTracker:
    """High-level position tracker delegating to SQLite database storage."""

    def __init__(self, db_path: str | Path = ":memory:", db: Database | None = None) -> None:
        self.db = db if db is not None else Database(db_path)

    def apply(self, event: OrderEvent) -> bool:
        """Apply an order event atomically. Returns True if accepted, False if duplicate."""
        return self.db.apply_event(event)

    def snapshot(self) -> dict[str, int]:
        """Return snapshot dictionary of current net positions for all symbols."""
        return self.db.get_positions()

    def get_symbol_position(self, symbol: str) -> dict[str, Any] | None:
        """Return position details for a specific symbol."""
        return self.db.get_position(symbol)

    def reconcile(self) -> dict[str, Any]:
        """Verify consistency between event audit logs and positions table."""
        return self.db.reconcile()

    def is_healthy(self) -> bool:
        """Check if underlying database storage is healthy and responsive."""
        return self.db.is_healthy()

    def reset(self) -> None:
        """Reset positions and event history."""
        self.db.reset()

    def close(self) -> None:
        """Cleanly close database connections."""
        self.db.close()