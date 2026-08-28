from __future__ import annotations

from typing import Dict, Literal

from pydantic import BaseModel, ConfigDict, Field


class OrderEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    transaction_type: Literal["BUY", "SELL"]
    quantity: int = Field(gt=0)


class ValidationResult(BaseModel):
    valid: bool
    event: OrderEvent | None = None
    reason: str | None = None


PositionResponse = Dict[str, int]
