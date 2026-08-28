from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Any

from src.common.models import OrderEvent


class Database:
    """Persistent SQLite storage for trading positions and audit events."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self._lock = Lock()
        
        # Connect to SQLite. check_same_thread=False allows multi-threaded access protected by self._lock
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=10.0,
            isolation_level=None,  # We manage transactions explicitly
        )
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            # Enable Write-Ahead Logging for better concurrency when using file-based DB
            if self.db_path != ":memory:":
                cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=5000;")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    net_position INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    processed_at TEXT NOT NULL
                );
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_symbol ON events (symbol);
                """
            )

    def apply_event(self, event: OrderEvent) -> bool:
        """Atomically record event and update symbol position in a single transaction.
        
        Returns True if event was accepted, or False if it was already processed (duplicate).
        """
        now = datetime.now(timezone.utc).isoformat()
        delta = event.quantity if event.transaction_type == "BUY" else -event.quantity

        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                # 1. Attempt to insert into events table for durable deduplication
                cursor.execute(
                    """
                    INSERT INTO events (event_id, symbol, transaction_type, quantity, processed_at)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (event.event_id, event.symbol, event.transaction_type, event.quantity, now),
                )

                # 2. Atomic UPSERT for position
                cursor.execute(
                    """
                    INSERT INTO positions (symbol, net_position, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        net_position = positions.net_position + excluded.net_position,
                        updated_at = excluded.updated_at;
                    """,
                    (event.symbol, delta, now),
                )

                cursor.execute("COMMIT;")
                return True
            except sqlite3.IntegrityError:
                # event_id already exists in events table
                cursor.execute("ROLLBACK;")
                return False
            except Exception:
                cursor.execute("ROLLBACK;")
                raise

    def get_positions(self) -> dict[str, int]:
        """Return a snapshot of all symbol net positions."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT symbol, net_position FROM positions ORDER BY symbol ASC;")
            rows = cursor.fetchall()
            return {row["symbol"]: row["net_position"] for row in rows}

    def get_position(self, symbol: str) -> dict[str, Any] | None:
        """Return position details for a specific symbol, or None if not found."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT symbol, net_position, updated_at FROM positions WHERE symbol = ?;",
                (symbol,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {
                "symbol": row["symbol"],
                "net_position": row["net_position"],
                "updated_at": row["updated_at"],
            }

    def reconcile(self) -> dict[str, Any]:
        """Audit reconciliation: recalculates positions from historical events and verifies consistency."""
        with self._lock:
            cursor = self._conn.cursor()
            # Calculate sum of events per symbol
            cursor.execute(
                """
                SELECT 
                    symbol,
                    SUM(CASE WHEN transaction_type = 'BUY' THEN quantity ELSE -quantity END) as calculated_position,
                    COUNT(*) as event_count
                FROM events
                GROUP BY symbol;
                """
            )
            audit_rows = cursor.fetchall()
            audit_map = {row["symbol"]: row["calculated_position"] for row in audit_rows}

            # Fetch current stored positions
            cursor.execute("SELECT symbol, net_position FROM positions;")
            stored_rows = cursor.fetchall()
            stored_map = {row["symbol"]: row["net_position"] for row in stored_rows}

            discrepancies = []
            all_symbols = set(audit_map.keys()) | set(stored_map.keys())
            for sym in sorted(all_symbols):
                stored_val = stored_map.get(sym, 0)
                audit_val = audit_map.get(sym, 0)
                if stored_val != audit_val:
                    discrepancies.append(
                        {
                            "symbol": sym,
                            "stored_position": stored_val,
                            "calculated_position": audit_val,
                        }
                    )

            is_consistent = len(discrepancies) == 0
            return {
                "status": "consistent" if is_consistent else "discrepancy_detected",
                "is_consistent": is_consistent,
                "total_symbols": len(all_symbols),
                "discrepancies": discrepancies,
                "positions": stored_map,
            }

    def is_healthy(self) -> bool:
        """Check if database connection is alive."""
        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute("SELECT 1;")
                return cursor.fetchone() is not None
        except Exception:
            return False

    def reset(self) -> None:
        """Reset state by truncating tables (used for testing)."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute("DELETE FROM positions;")
                cursor.execute("DELETE FROM events;")
                cursor.execute("COMMIT;")
            except Exception:
                cursor.execute("ROLLBACK;")
                raise

    def close(self) -> None:
        """Close database connection."""
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass
