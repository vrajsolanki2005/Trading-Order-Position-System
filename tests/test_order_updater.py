from pathlib import Path

from src.order_updater.main import process_file


def test_invalid_row_does_not_stop_later_rows(tmp_path, monkeypatch):
    csv_file = tmp_path / "orders.csv"
    csv_file.write_text(
        "event_id,symbol,transaction_type,quantity\n"
        "evt-1,A,BUY,10\n"
        "evt-bad,A,HOLD,5\n"
        "evt-2,A,SELL,3\n",
        encoding="utf-8",
    )

    sent = []

    class FakeSender:
        def __init__(self, *args, **kwargs):
            pass
        def send(self, event):
            sent.append(event)
            return "accepted"
        def close(self):
            pass

    monkeypatch.setattr("src.order_updater.main.EventSender", FakeSender)
    summary = process_file(str(csv_file), "http://unused", rate_limit=0)
    assert [event.event_id for event in sent] == ["evt-1", "evt-2"]
    assert summary == {"accepted": 2, "rejected": 1, "duplicates": 0, "sent": 2}


def test_duplicate_id_first_valid_row_wins(tmp_path, monkeypatch):
    csv_file = tmp_path / "orders.csv"
    csv_file.write_text(
        "event_id,symbol,transaction_type,quantity\n"
        "evt-1,A,BUY,10\n"
        "evt-1,A,SELL,999\n"
        "evt-2,A,BUY,5\n",
        encoding="utf-8",
    )
    sent = []

    class FakeSender:
        def __init__(self, *args, **kwargs): pass
        def send(self, event): sent.append(event); return "accepted"
        def close(self): pass

    monkeypatch.setattr("src.order_updater.main.EventSender", FakeSender)
    summary = process_file(str(csv_file), "http://unused", rate_limit=0)
    assert [e.event_id for e in sent] == ["evt-1", "evt-2"]
    assert summary["duplicates"] == 1


def test_rate_limiter_compliance():
    import time
    from src.common.rate_limiter import IntervalRateLimiter

    rate = 100.0  # 100 events/sec -> 10ms per event
    limiter = IntervalRateLimiter(rate)
    start = time.perf_counter()
    for _ in range(10):
        limiter.wait()
    duration = time.perf_counter() - start
    # 9 intervals between 10 events => expected ~0.09s (allow a small tolerance for fast execution)
    assert duration >= 0.07


def test_client_retries_on_500_and_succeeds():
    import httpx
    from src.common.models import OrderEvent
    from src.order_updater.client import EventSender

    attempts = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(500, text="Internal Error", request=request)
        return httpx.Response(200, json={"status": "accepted"}, request=request)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)
    sender = EventSender("http://testserver", rate_limit=0, retry_count=2, backoff=0.01, client=client)

    ev = OrderEvent(event_id="e-1", symbol="AAPL", transaction_type="BUY", quantity=10)
    status = sender.send(ev)
    assert status == "accepted"
    assert attempts == 2


def test_client_does_not_retry_4xx():
    import pytest
    import httpx
    from src.common.models import OrderEvent
    from src.order_updater.client import EventSender

    attempts = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(422, json={"detail": "Unprocessable"}, request=request)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)
    sender = EventSender("http://testserver", rate_limit=0, retry_count=3, backoff=0.01, client=client)

    ev = OrderEvent(event_id="e-1", symbol="AAPL", transaction_type="BUY", quantity=10)
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        sender.send(ev)

    assert exc_info.value.response.status_code == 422
    assert attempts == 1  # 4xx must fail immediately without retries


def test_reader_missing_headers(tmp_path):
    import pytest
    from src.order_updater.reader import read_csv_rows

    csv_file = tmp_path / "bad_header.csv"
    csv_file.write_text("event_id,symbol\n1,AAPL\n", encoding="utf-8")

    with pytest.raises(ValueError, match="CSV missing required columns"):
        list(read_csv_rows(csv_file))

