
import logging

from fastapi import FastAPI
from pydantic import BaseModel

from src.common.models import OrderEvent
from .tracker import PositionTracker

logger = logging.getLogger(__name__)


class EventResponse(BaseModel):
    status: str


def create_app(tracker: PositionTracker | None = None) -> FastAPI:
    tracker = tracker or PositionTracker()
    app = FastAPI(title="Position Maintaining Service", version="1.0.0")
    app.state.tracker = tracker

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/events", response_model=EventResponse)
    def receive_event(event: OrderEvent) -> EventResponse:
        if tracker.apply(event):
            logger.info("Accepted event %s", event.event_id)
            return EventResponse(status="accepted")

        logger.info("Duplicate event %s ignored", event.event_id)
        return EventResponse(status="duplicate")

    @app.get("/position")
    def get_position() -> dict[str, int]:
        return tracker.snapshot()

    @app.post("/reset")
    def reset() -> dict[str, str]:
        tracker.reset()
        logger.info("Position state reset")
        return {"status": "reset"}

    return app


app = create_app()