from typing import Dict, Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_QUANTITY = 1_000_000_000_000
MAX_EVENT_ID_LEN = 128
MAX_SYMBOL_LEN = 32


class OrderEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=MAX_EVENT_ID_LEN)
    symbol: str = Field(min_length=1, max_length=MAX_SYMBOL_LEN)
    transaction_type: Literal["BUY", "SELL"]
    quantity: int = Field(gt=0, le=MAX_QUANTITY)


class ValidationResult(BaseModel):
    valid: bool
    event: OrderEvent | None = None
    reason: str | None = None


PositionResponse = Dict[str, int]
