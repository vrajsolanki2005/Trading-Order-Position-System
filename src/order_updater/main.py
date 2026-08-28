from __future__ import annotations

import argparse
import logging

from src.common.logger import configure_logging
from src.common.validator import validate_row
from .client import EventSender
from .reader import read_csv_rows

logger = logging.getLogger(__name__)


def process_file(
    csv_file: str,
    service_url: str,
    rate_limit: float = 50,
    retry_count: int = 2,
    timeout: float = 5.0,
) -> dict[str, int]:
    accepted = rejected = sent = duplicates = 0
    seen_event_ids: set[str] = set()
    sender = EventSender(
        service_url,
        rate_limit=rate_limit,
        retry_count=retry_count,
        timeout=timeout,
    )

    try:
        for row_number, row in read_csv_rows(csv_file):
            result = validate_row(row)
            if not result.valid:
                rejected += 1
                logger.warning("Rejected row %d: %s", row_number, result.reason)
                continue

            event = result.event
            if event is None:
                rejected += 1
                logger.warning("Row %d produced no event payload", row_number)
                continue

            if event.event_id in seen_event_ids:
                logger.info("Duplicate event_id %s ignored", event.event_id)
                duplicates += 1
                continue

            seen_event_ids.add(event.event_id)
            accepted += 1
            logger.info("Accepted event %s", event.event_id)

            try:
                status = sender.send(event)
            except Exception as exc:
                logger.error("Failed to send event %s: %s", event.event_id, exc)
                raise

            sent += 1
            logger.info("Sent event %s successfully (%s)", event.event_id, status)
    finally:
        sender.close()

    summary = {
        "accepted": accepted,
        "rejected": rejected,
        "duplicates": duplicates,
        "sent": sent,
    }
    logger.info("Input processing complete: %s", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream order updates to the Position Service")
    parser.add_argument("--csv-file", required=True)
    parser.add_argument("--service-url", default="http://127.0.0.1:8000")
    parser.add_argument("--rate-limit", type=float, default=50)
    parser.add_argument("--retry-count", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)
    process_file(
        args.csv_file,
        args.service_url,
        rate_limit=args.rate_limit,
        retry_count=args.retry_count,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()