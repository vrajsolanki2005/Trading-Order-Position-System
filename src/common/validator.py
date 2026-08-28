
from collections.abc import Mapping
from typing import Any

from .models import OrderEvent, ValidationResult


def _required_text(row: Mapping[str, Any], field: str) -> tuple[str | None, str | None]:
    value = row.get(field)
    if value is None:
        return None, f"missing {field}"

    text = str(value).strip()
    if text == "":
        return None, f"{field} must be non-empty"
    return text, None


def _parse_quantity(value: Any) -> int | None:
    if value is None:
        return None

    text = str(value).strip()
    if text == "" or not text.isascii() or not text.isdigit():
        return None

    quantity = int(text)
    return quantity if quantity > 0 else None


def validate_row(row: Mapping[str, Any]) -> ValidationResult:
    if not isinstance(row, Mapping):
        return ValidationResult(valid=False, reason="row must be a mapping")

    if None in row and row[None]:
        return ValidationResult(valid=False, reason="row contains extra columns")

    event_id, error = _required_text(row, "event_id")
    if error:
        return ValidationResult(valid=False, reason=error)

    symbol, error = _required_text(row, "symbol")
    if error:
        return ValidationResult(valid=False, reason=error)

    if row.get("transaction_type") not in ("BUY", "SELL"):
        return ValidationResult(
            valid=False,
            reason="transaction_type must be exactly BUY or SELL",
        )

    quantity = _parse_quantity(row.get("quantity"))
    if quantity is None:
        return ValidationResult(valid=False, reason="quantity must be a positive integer")

    try:
        event = OrderEvent(
            event_id=event_id,
            symbol=symbol,
            transaction_type=row["transaction_type"],
            quantity=quantity,
        )
    except ValueError as exc:
        return ValidationResult(valid=False, reason=str(exc))

    return ValidationResult(valid=True, event=event)