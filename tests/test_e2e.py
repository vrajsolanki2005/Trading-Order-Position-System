from fastapi.testclient import TestClient

from src.order_updater.main import process_file
from src.position_service.server import create_app
from src.position_service.tracker import PositionTracker


def test_end_to_end(tmp_path, monkeypatch):
    csv_file = tmp_path / "orders.csv"
    csv_file.write_text(
        "event_id,symbol,transaction_type,quantity\n"
        "evt-1,RELIANCE,BUY,90\n"
        "evt-2,TCS,SELL,75\n"
        "evt-3,RELIANCE,SELL,90\n"
        "evt-4,TCS,BUY,75\n"
        "evt-3,TCS,BUY,999\n",
        encoding="utf-8",
    )

    client = TestClient(create_app(PositionTracker()))

    class TestSender:
        def __init__(self, *args, **kwargs): pass
        def send(self, event):
            response = client.post("/events", json=event.model_dump())
            response.raise_for_status()
            return response.json()["status"]
        def close(self): pass

    monkeypatch.setattr("src.order_updater.main.EventSender", TestSender)
    summary = process_file(str(csv_file), "http://test", rate_limit=0)
    assert summary == {"accepted": 4, "rejected": 0, "duplicates": 1, "sent": 4}
    assert client.get("/position").json() == {"RELIANCE": 0, "TCS": 0}


def test_sample_order_updates_e2e(monkeypatch):
    from pathlib import Path

    sample_csv = Path(__file__).parent.parent / "sample_data" / "order_updates.csv"
    assert sample_csv.exists()

    client = TestClient(create_app(PositionTracker()))

    class TestSender:
        def __init__(self, *args, **kwargs): pass
        def send(self, event):
            response = client.post("/events", json=event.model_dump())
            response.raise_for_status()
            return response.json()["status"]
        def close(self): pass

    monkeypatch.setattr("src.order_updater.main.EventSender", TestSender)
    summary = process_file(str(sample_csv), "http://test", rate_limit=0)
    assert summary == {"accepted": 7, "rejected": 0, "duplicates": 0, "sent": 7}
    assert client.get("/position").json() == {"RELIANCE": 0, "TCS": 0, "INFY": 0}


def test_sample_edge_cases_e2e(monkeypatch):
    from pathlib import Path

    sample_csv = Path(__file__).parent.parent / "sample_data" / "edge_cases.csv"
    assert sample_csv.exists()

    client = TestClient(create_app(PositionTracker()))

    class TestSender:
        def __init__(self, *args, **kwargs): pass
        def send(self, event):
            response = client.post("/events", json=event.model_dump())
            response.raise_for_status()
            return response.json()["status"]
        def close(self): pass

    monkeypatch.setattr("src.order_updater.main.EventSender", TestSender)
    summary = process_file(str(sample_csv), "http://test", rate_limit=0)
    assert summary == {"accepted": 3, "rejected": 8, "duplicates": 1, "sent": 3}
    assert client.get("/position").json() == {"RELIANCE": 90, "TCS": 0}

