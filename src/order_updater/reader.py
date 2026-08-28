from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def read_csv_rows(path: str | Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with open(path, "r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV file has no header")
        required = {"event_id", "symbol", "transaction_type", "quantity"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")

        for row_number, row in enumerate(reader, start=2):
            yield row_number, row