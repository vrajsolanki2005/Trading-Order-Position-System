from concurrent.futures import ThreadPoolExecutor

from src.common.models import OrderEvent
from src.position_service.tracker import PositionTracker


def event(event_id, symbol="RELIANCE", transaction_type="BUY", quantity=10):
    return OrderEvent(event_id=event_id, symbol=symbol, transaction_type=transaction_type, quantity=quantity)


def test_buy_and_sell():
    tracker = PositionTracker()
    assert tracker.apply(event("1", quantity=90))
    assert tracker.apply(event("2", transaction_type="SELL", quantity=25))
    assert tracker.snapshot() == {"RELIANCE": 65}


def test_multiple_symbols_negative_and_zero_positions():
    tracker = PositionTracker()
    tracker.apply(event("1", "A", "SELL", 10))
    tracker.apply(event("2", "B", "BUY", 10))
    tracker.apply(event("3", "B", "SELL", 10))
    assert tracker.snapshot() == {"A": -10, "B": 0}


def test_duplicate_event_id_wins_first_payload():
    tracker = PositionTracker()
    assert tracker.apply(event("same", "A", "BUY", 10))
    assert not tracker.apply(event("same", "A", "SELL", 999))
    assert tracker.snapshot() == {"A": 10}


def test_concurrent_updates_are_atomic():
    tracker = PositionTracker()
    # 500 BUY and 500 SELL of 1 unit -> net 0
    events = [event(f"buy-{i}", "A", "BUY", 1) for i in range(500)] + [
        event(f"sell-{i}", "A", "SELL", 1) for i in range(500)
    ]
    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(tracker.apply, events))
    assert all(results)
    assert tracker.snapshot() == {"A": 0}


def test_reset():
    tracker = PositionTracker()
    tracker.apply(event("1", "A", "BUY", 50))
    assert tracker.snapshot() == {"A": 50}
    tracker.reset()
    assert tracker.snapshot() == {}
    # After reset, event_id "1" can be accepted again
    assert tracker.apply(event("1", "A", "SELL", 20))
    assert tracker.snapshot() == {"A": -20}

