
from threading import Lock

from src.common.models import OrderEvent


class PositionTracker:
    def __init__(self) -> None:
        self._positions: dict[str, int] = {}
        self._seen_event_ids: set[str] = set()
        self._lock = Lock()

    def apply(self, event: OrderEvent) -> bool:
        with self._lock:
            if event.event_id in self._seen_event_ids:
                return False

            delta = event.quantity if event.transaction_type == "BUY" else -event.quantity
            self._positions[event.symbol] = self._positions.get(event.symbol, 0) + delta
            self._seen_event_ids.add(event.event_id)
            return True

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._positions)

    def reset(self) -> None:
        with self._lock:
            self._positions.clear()
            self._seen_event_ids.clear()