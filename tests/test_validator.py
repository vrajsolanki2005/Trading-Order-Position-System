from src.common.validator import validate_row


def row(**overrides):
    data = {"event_id": "evt-1", "symbol": "RELIANCE", "transaction_type": "BUY", "quantity": "10"}
    data.update(overrides)
    return data


def test_valid_row_preserves_symbol_case():
    result = validate_row(row(symbol="rElIaNcE"))
    assert result.valid
    assert result.event is not None
    assert result.event.symbol == "rElIaNcE"
    assert result.event.quantity == 10


def test_valid_row_whitespace_quantity():
    result = validate_row(row(quantity="  250  "))
    assert result.valid
    assert result.event is not None
    assert result.event.quantity == 250


def test_blank_event_id():
    assert not validate_row(row(event_id="")).valid
    assert not validate_row(row(event_id="   ")).valid


def test_blank_symbol():
    assert not validate_row(row(symbol="")).valid
    assert not validate_row(row(symbol="   ")).valid


def test_invalid_transaction_types():
    for value in ["HOLD", "buy", "Sell", "BUY1", "", 123, None]:
        result = validate_row(row(transaction_type=value))
        assert not result.valid
        assert "transaction_type" in (result.reason or "")


def test_invalid_quantities():
    for value in ["0", "-1", "-999", "1.5", "3.14", "abc", "", " ", None]:
        result = validate_row(row(quantity=value))
        assert not result.valid
        assert "quantity" in (result.reason or "")


def test_missing_columns_are_rejected():
    assert not validate_row({"event_id": "evt-1"}).valid
    assert not validate_row({"event_id": "evt-1", "symbol": "TCS"}).valid
    assert not validate_row({"event_id": "evt-1", "symbol": "TCS", "transaction_type": "BUY"}).valid


def test_extra_columns_are_rejected():
    data = row()
    data[None] = ["unexpected_column_value"]
    result = validate_row(data)
    assert not result.valid
    assert "extra columns" in (result.reason or "")


def test_non_mapping_input():
    assert not validate_row(None).valid  # type: ignore
    assert not validate_row("invalid").valid  # type: ignore

