import time
from collections import defaultdict, deque
from typing import Dict, Tuple
from fastapi import HTTPException, Request, status

from app.core.config import settings


class LoginRateLimiter:
    """
    Sliding window in-memory rate limiter for login attempts.
    Tracks timestamps of attempts per client key (e.g. IP address).
    """

    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: Dict[str, deque] = defaultdict(deque)

    def _get_client_key(self, request: Request, identifier: str = "") -> str:
        # Check X-Forwarded-For first, fallback to client host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "127.0.0.1"

        return f"{client_ip}:{identifier.lower()}" if identifier else client_ip

    def check_rate_limit(self, request: Request, identifier: str = "") -> None:
        """
        Validates whether the client has exceeded login attempt limits.
        Raises HTTP 429 if the limit is exceeded.
        """
        key = self._get_client_key(request, identifier)
        now = time.time()
        window_start = now - self.window_seconds

        queue = self._attempts[key]
        # Remove timestamps outside the sliding window
        while queue and queue[0] < window_start:
            queue.popleft()

        if len(queue) >= self.max_attempts:
            retry_after = int(self.window_seconds - (now - queue[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

        queue.append(now)

    def reset(self, key: str = "") -> None:
        """Resets rate limit entries for a specific key or all keys."""
        if key:
            self._attempts.pop(key, None)
        else:
            self._attempts.clear()


login_rate_limiter = LoginRateLimiter(
    max_attempts=settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
    window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
)
