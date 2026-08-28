from fastapi.testclient import TestClient

from src.position_service.server import create_app
from src.position_service.tracker import PositionTracker


def test_get_position_response_and_duplicate():
    client = TestClient(create_app(PositionTracker()))
    event = {"event_id": "evt-1", "symbol": "TCS", "transaction_type": "SELL", "quantity": 75}
    assert client.post("/events", json=event).json() == {"status": "accepted"}
    duplicate = {**event, "transaction_type": "BUY", "quantity": 999}
    assert client.post("/events", json=duplicate).json() == {"status": "duplicate"}
    assert client.get("/position").json() == {"TCS": -75}


def test_api_rejects_invalid_event():
    client = TestClient(create_app(PositionTracker()))
    response = client.post(
        "/events",
        json={"event_id": "x", "symbol": "TCS", "transaction_type": "HOLD", "quantity": 1},
    )
    assert response.status_code == 422


def test_health():
    client = TestClient(create_app(PositionTracker()))
    assert client.get("/health").json() == {"status": "ok"}


def test_reset_endpoint():
    client = TestClient(create_app(PositionTracker()))
    client.post("/events", json={"event_id": "evt-1", "symbol": "INFY", "transaction_type": "BUY", "quantity": 100})
    assert client.get("/position").json() == {"INFY": 100}
    reset_resp = client.post("/reset")
    assert reset_resp.status_code == 200
    assert reset_resp.json() == {"status": "reset"}
    assert client.get("/position").json() == {}


def test_concurrent_api_requests():
    from concurrent.futures import ThreadPoolExecutor

    client = TestClient(create_app(PositionTracker()))

    def post_order(i):
        return client.post(
            "/events",
            json={"event_id": f"evt-{i}", "symbol": "AAPL", "transaction_type": "BUY", "quantity": 1},
        ).status_code

    def get_pos():
        return client.get("/position").status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        post_futures = [executor.submit(post_order, i) for i in range(100)]
        get_futures = [executor.submit(get_pos) for _ in range(50)]

    for f in post_futures:
        assert f.result() == 200
    for f in get_futures:
        assert f.result() == 200

    assert client.get("/position").json() == {"AAPL": 100}

