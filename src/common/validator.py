from collections.abc import Mapping
from typing import Any

from .models import MAX_EVENT_ID_LEN, MAX_QUANTITY, MAX_SYMBOL_LEN, OrderEvent, ValidationResult


def _required_text(row: Mapping[str, Any], field: str, max_length: int) -> tuple[str | None, str | None]:
    value = row.get(field)
    if value is None:
        return None, f"missing {field}"

    text = str(value).strip()
    if text == "":
        return None, f"{field} must be non-empty"
    if len(text) > max_length:
        return None, f"{field} exceeds maximum length of {max_length}"
    return text, None


def _parse_quantity(value: Any) -> tuple[int | None, str | None]:
    if value is None:
        return None, "missing quantity"

    text = str(value).strip()
    if text == "" or not text.isascii() or not text.isdigit():
        return None, "quantity must be a positive integer"

    try:
        quantity = int(text)
    except ValueError:
        return None, "quantity must be a positive integer"

    if quantity <= 0:
        return None, "quantity must be a positive integer"
    if quantity > MAX_QUANTITY:
        return None, f"quantity exceeds maximum allowed limit of {MAX_QUANTITY}"

    return quantity, None


def validate_row(row: Mapping[str, Any]) -> ValidationResult:
    if not isinstance(row, Mapping):
        return ValidationResult(valid=False, reason="row must be a mapping")

    if None in row and row[None]:
        return ValidationResult(valid=False, reason="row contains extra columns")

    event_id, error = _required_text(row, "event_id", MAX_EVENT_ID_LEN)
    if error:
        return ValidationResult(valid=False, reason=error)

    symbol, error = _required_text(row, "symbol", MAX_SYMBOL_LEN)
    if error:
        return ValidationResult(valid=False, reason=error)

    if row.get("transaction_type") not in ("BUY", "SELL"):
        return ValidationResult(
            valid=False,
            reason="transaction_type must be exactly BUY or SELL",
        )

    quantity, error = _parse_quantity(row.get("quantity"))
    if error:
        return ValidationResult(valid=False, reason=error)

    try:
        assert event_id is not None
        assert symbol is not None
        assert quantity is not None
        event = OrderEvent(
            event_id=event_id,
            symbol=symbol,
            transaction_type=row["transaction_type"],
            quantity=quantity,
        )
    except ValueError as exc:
        return ValidationResult(valid=False, reason=str(exc))

    return ValidationResult(valid=True, event=event)