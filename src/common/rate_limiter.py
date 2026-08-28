
import time


class IntervalRateLimiter:
    def __init__(self, rate: float, clock=time.monotonic, sleeper=time.sleep) -> None:
        if rate < 0:
            raise ValueError("rate must be >= 0")
        self.rate = rate
        self.interval = 0.0 if rate == 0 else 1.0 / rate
        self._clock = clock
        self._sleep = sleeper
        self._next_allowed = clock()

    def wait(self) -> None:
        if self.interval == 0.0:
            return

        now = self._clock()
        delay = self._next_allowed - now
        if delay > 0:
            self._sleep(delay)
            now = self._clock()

        self._next_allowed = max(self._next_allowed, now) + self.interval