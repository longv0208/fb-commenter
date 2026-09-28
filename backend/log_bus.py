"""Per-account log bus: logging.Handler → asyncio.Queue subscribers."""
import asyncio
import logging
import re
import time

_SECRET_RE = re.compile(
    r"(?i)(xs|c_user|access_token|password|cookie)\s*[:=]\s*[^\s,}\"']+"
)


def _scrub(text):
    return _SECRET_RE.sub(r"\1=<redacted>", str(text))


class LogBus(logging.Handler):
    """Broadcast log records to per-account async subscriber queues."""

    def __init__(self, max_queue=1000):
        super().__init__()
        self._subscribers = {}  # account -> set[asyncio.Queue]
        self._loop = None
        self._max_queue = max_queue

    def bind_loop(self, loop):
        self._loop = loop

    def emit(self, record):
        account = getattr(record, "account", "system")
        entry = {
            "ts": time.time(),
            "level": record.levelname,
            "account": account,
            "logger": record.name,
            "msg": _scrub(self.format(record)),
        }
        for key in (account, "*"):
            for queue in self._subscribers.get(key, ()):
                self._push(queue, entry)

    def _push(self, queue, entry):
        try:
            queue.put_nowait(entry)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()  # drop oldest
                queue.put_nowait(entry)
            except Exception:
                pass

    async def subscribe(self, account="*"):
        """Async iterator yielding log entries for account ('*' = all)."""
        queue = asyncio.Queue(maxsize=self._max_queue)
        self._subscribers.setdefault(account, set()).add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.get(account, set()).discard(queue)


log_bus = LogBus()


def attach_root():
    """Attach the global bus to the root logger once."""
    root = logging.getLogger()
    if log_bus not in root.handlers:
        root.addHandler(log_bus)
