import time
from typing import Dict

class TokenRevocationList:
    """TRL em memória (SQLite-backed opcional). Revogação instantânea de JWTs pelo jti."""
    _store: Dict[str, float] = {}

    @classmethod
    def revoke(cls, jti: str, exp: float):
        cls._store[jti] = exp

    @classmethod
    def is_revoked(cls, jti: str) -> bool:
        cls._purge()
        return jti in cls._store

    @classmethod
    def _purge(cls):
        now = time.time()
        expired = [k for k, v in cls._store.items() if v < now]
        for k in expired:
            del cls._store[k]
