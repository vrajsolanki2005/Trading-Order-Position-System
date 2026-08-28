from pathlib import Path

from src.common.models import OrderEvent
from src.position_service.tracker import PositionTracker


def test_sqlite_persistence_restart_recovery(tmp_path: Path) -> None:
    db_file = tmp_path / "positions_test.db"

    # 1. Start tracker instance with persistent SQLite database
    tracker1 = PositionTracker(db_path=db_file)
    assert tracker1.apply(OrderEvent(event_id="evt-1", symbol="RELIANCE", transaction_type="BUY", quantity=100))
    assert tracker1.apply(OrderEvent(event_id="evt-2", symbol="RELIANCE", transaction_type="SELL", quantity=30))
    assert tracker1.apply(OrderEvent(event_id="evt-3", symbol="TCS", transaction_type="BUY", quantity=50))
    
    assert tracker1.snapshot() == {"RELIANCE": 70, "TCS": 50}
    tracker1.close()

    # 2. Simulate service restart: create a new tracker instance pointing to same db file
    tracker2 = PositionTracker(db_path=db_file)
    assert tracker2.snapshot() == {"RELIANCE": 70, "TCS": 50}

    # 3. Verify durable idempotency: evt-1 should be rejected as duplicate even after restart
    assert not tracker2.apply(OrderEvent(event_id="evt-1", symbol="RELIANCE", transaction_type="BUY", quantity=999))
    assert tracker2.snapshot() == {"RELIANCE": 70, "TCS": 50}

    # 4. New events continue to process properly
    assert tracker2.apply(OrderEvent(event_id="evt-4", symbol="TCS", transaction_type="SELL", quantity=20))
    assert tracker2.snapshot() == {"RELIANCE": 70, "TCS": 30}
    tracker2.close()


def test_audit_reconciliation() -> None:
    tracker = PositionTracker()  # in-memory DB
    tracker.apply(OrderEvent(event_id="e1", symbol="INFY", transaction_type="BUY", quantity=100))
    tracker.apply(OrderEvent(event_id="e2", symbol="INFY", transaction_type="BUY", quantity=50))
    tracker.apply(OrderEvent(event_id="e3", symbol="INFY", transaction_type="SELL", quantity=25))
    tracker.apply(OrderEvent(event_id="e4", symbol="WIPRO", transaction_type="BUY", quantity=10))

    report = tracker.reconcile()
    assert report["status"] == "consistent"
    assert report["is_consistent"] is True
    assert report["total_symbols"] == 2
    assert report["positions"] == {"INFY": 125, "WIPRO": 10}
    assert report["discrepancies"] == []
