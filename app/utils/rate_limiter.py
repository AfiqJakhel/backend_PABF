"""
In-memory, thread-safe rate limiter untuk endpoint sensitif seperti login.
Mencatat jumlah percobaan gagal per key (misal IP + NIM) dalam jendela waktu tertentu.
"""

import time
from threading import Lock

class SimpleRateLimiter:
    def __init__(self):
        self._lock = Lock()
        # key -> list of timestamps (float)
        self._attempts = {}

    def is_rate_limited(self, key: str, max_attempts: int, window_seconds: int) -> bool:
        """
        Mengecek apakah key telah melebihi max_attempts dalam window_seconds terakhir.
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            timestamps = self._attempts.get(key, [])
            # Filter hanya timestamp yang masih dalam jendela waktu
            valid_timestamps = [t for t in timestamps if t > cutoff]
            self._attempts[key] = valid_timestamps
            return len(valid_timestamps) >= max_attempts

    def record_attempt(self, key: str, window_seconds: int = 900) -> None:
        """
        Mencatat satu percobaan (misalnya login gagal).
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            timestamps = self._attempts.get(key, [])
            valid_timestamps = [t for t in timestamps if t > cutoff]
            valid_timestamps.append(now)
            self._attempts[key] = valid_timestamps

    def clear(self, key: str) -> None:
        """
        Menghapus riwayat percobaan jika login berhasil.
        """
        with self._lock:
            self._attempts.pop(key, None)


# Singleton instance
login_rate_limiter = SimpleRateLimiter()
