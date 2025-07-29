import logging
import threading
import time
from functools import wraps
from typing import ParamSpec, TypeVar, Callable


logger = logging.getLogger(__name__)


P = ParamSpec("P")
R = TypeVar("R")


class RateLimiter:
    def __init__(self, max_calls_per_minute: int):
        self.max_calls_per_minute = max_calls_per_minute
        self.min_interval = 60 / max_calls_per_minute
        self.lock = threading.Lock()
        self.last_call = 0.0
        self.call_times = []  # лог вызовов

    def update_rate_limit(self, new_limit: int):
        self.max_calls_per_minute = new_limit
        self.min_interval = 60 / new_limit
        logger.info(
            f"update_rate_limit: {new_limit}, new min interval: {self.min_interval}"
        )

    def wait(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> Callable[P, R]:
        with self.lock:
            start_exec_time = time.time()
            wait_time = self.min_interval - (start_exec_time - self.last_call)
            if self.last_call and wait_time > 0:
                logger.info(f"wait befor call for: {wait_time} seconds")
                time.sleep(wait_time)

            self._log_call(time.time())
            self.last_call = time.time()
            result = func(*args, **kwargs)
            return result

    def _log_call(self, now):
        readable = time.strftime("%H:%M:%S", time.localtime(now))
        logger.info(f"[RateLimiter] Tool called at {readable}")

        # Добавляем новый вызов
        self.call_times.append(now)

        # Очистим старые вызовы (старше 60 сек) — если нужно контролировать окно
        one_minute_ago = now - 60
        self.call_times = [t for t in self.call_times if t >= one_minute_ago]

        # Проверка: если вдруг вызовов стало больше чем разрешено
        if len(self.call_times) > self.max_calls_per_minute:
            logger.info(
                f"[RateLimiter][WARNING] Exceeded rate: {len(self.call_times)} calls in the last minute"
            )


rate_limiter: RateLimiter = RateLimiter(10)


def rate_limited_tools_per_minute(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        result = rate_limiter.wait(func=func, *args, **kwargs)
        return result
    return wrapper

