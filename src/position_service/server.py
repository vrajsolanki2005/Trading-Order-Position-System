from contextlib import asynccontextmanager
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from src.common.models import OrderEvent
from .tracker import PositionTracker

logger = logging.getLogger(__name__)


class EventResponse(BaseModel):
    status: str = Field(description="Processing status: 'accepted' or 'duplicate'")


class SymbolPositionResponse(BaseModel):
    symbol: str
    net_position: int
    updated_at: str | None = None


def create_app(tracker: PositionTracker | None = None) -> FastAPI:
    tracker = tracker or PositionTracker()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        yield
        # Graceful shutdown: close database connections
        if hasattr(app.state, "tracker") and hasattr(app.state.tracker, "close"):
            app.state.tracker.close()

    app = FastAPI(
        title="Trading Order Position Service",
        description="Production-grade position maintaining service with SQLite persistence and durable deduplication.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.tracker = tracker

    @app.get("/health", summary="Liveness probe")
    def health() -> dict[str, str]:
        """Verify the service process is alive."""
        return {"status": "ok"}

    @app.get("/ready", summary="Readiness probe")
    def ready() -> dict[str, str]:
        """Verify the service and its persistent database storage are ready to accept traffic."""
        if not app.state.tracker.is_healthy():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database storage is not ready",
            )
        return {"status": "ready", "database": "connected"}

    @app.post("/events", response_model=EventResponse, summary="Ingest order event")
    @app.post("/api/v1/events", response_model=EventResponse, include_in_schema=False)
    def receive_event(event: OrderEvent) -> EventResponse:
        """Atomically record the order event and update the net position for the symbol."""
        if app.state.tracker.apply(event):
            logger.info("Accepted event %s for %s (%s %d)", event.event_id, event.symbol, event.transaction_type, event.quantity)
            return EventResponse(status="accepted")

        logger.info("Duplicate event %s ignored", event.event_id)
        return EventResponse(status="duplicate")

    @app.get("/position", summary="Get all positions")
    @app.get("/api/v1/positions", include_in_schema=False)
    def get_position() -> dict[str, int]:
        """Get the current net position for all symbols."""
        return app.state.tracker.snapshot()

    @app.get("/position/{symbol}", response_model=SymbolPositionResponse, summary="Get single symbol position")
    @app.get("/api/v1/positions/{symbol}", response_model=SymbolPositionResponse, include_in_schema=False)
    def get_symbol_position(symbol: str) -> SymbolPositionResponse:
        """Get the net position and last updated timestamp for a specific symbol."""
        pos = app.state.tracker.get_symbol_position(symbol)
        if pos is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No position found for symbol '{symbol}'",
            )
        return SymbolPositionResponse(
            symbol=pos["symbol"],
            net_position=pos["net_position"],
            updated_at=pos.get("updated_at"),
        )

    @app.get("/api/v1/reconcile", summary="Audit reconciliation")
    def reconcile() -> dict[str, Any]:
        """Perform on-demand consistency audit by recalculating positions from raw events."""
        return app.state.tracker.reconcile()

    @app.post("/reset", summary="Reset state")
    def reset() -> dict[str, str]:
        """Clear all stored positions and events (useful for test isolation)."""
        app.state.tracker.reset()
        logger.info("Position state reset")
        return {"status": "reset"}

    return app


app = create_app()