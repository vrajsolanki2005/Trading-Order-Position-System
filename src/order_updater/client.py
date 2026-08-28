
import logging
import time

import httpx

from src.common.models import OrderEvent
from src.common.rate_limiter import IntervalRateLimiter

logger = logging.getLogger(__name__)


class EventSender:
    def __init__(
        self,
        service_url: str,
        rate_limit: float = 50,
        timeout: float = 5.0,
        retry_count: int = 2,
        backoff: float = 0.25,
        client: httpx.Client | None = None,
    ) -> None:
        self.url = service_url.rstrip("/") + "/events"
        self.retry_count = max(0, retry_count)
        self.backoff = max(0.0, backoff)
        self.rate_limiter = IntervalRateLimiter(rate_limit)
        self.client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def send(self, event: OrderEvent) -> str:
        last_error: Exception | None = None
        for attempt in range(self.retry_count + 1):
            self.rate_limiter.wait()
            try:
                response = self.client.post(self.url, json=event.model_dump())
                if 400 <= response.status_code < 500:
                    logger.error(
                        "Client error (%d) sending event %s: %s",
                        response.status_code,
                        event.event_id,
                        response.text,
                    )
                    response.raise_for_status()

                if 500 <= response.status_code < 600:
                    raise httpx.HTTPStatusError(
                        f"Server returned {response.status_code}: {response.text}",
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                payload = response.json()
                return str(payload.get("status", "accepted"))
            except httpx.HTTPStatusError as exc:
                if 400 <= exc.response.status_code < 500:
                    raise
                last_error = exc
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc

            if attempt >= self.retry_count:
                break

            delay = self.backoff * (2**attempt)
            logger.warning(
                "Delivery attempt %d/%d failed for %s: %s; retrying in %.2fs",
                attempt + 1,
                self.retry_count + 1,
                event.event_id,
                last_error,
                delay,
            )
            time.sleep(delay)

        assert last_error is not None
        raise last_error
