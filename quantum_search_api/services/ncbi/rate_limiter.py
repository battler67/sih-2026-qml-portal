from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, requests_per_second: float) -> None:
        self.interval = 1.0 / max(requests_per_second, 0.1)
        self._next_at = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        if now < self._next_at:
            time.sleep(self._next_at - now)
        self._next_at = time.monotonic() + self.interval
