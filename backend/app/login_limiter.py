"""Limitador simples de tentativas de login por origem e usuário.

É adequado para a implantação atual com um único processo. Se a aplicação
passar a usar múltiplos workers, o armazenamento deve migrar para Redis ou
outro serviço compartilhado.
"""
from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class LoginRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _discard_expired(self, attempts: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()

    def is_blocked(self, key: str) -> bool:
        now = monotonic()
        with self._lock:
            attempts = self._attempts[key]
            self._discard_expired(attempts, now)
            return len(attempts) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        now = monotonic()
        with self._lock:
            attempts = self._attempts[key]
            self._discard_expired(attempts, now)
            attempts.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()
