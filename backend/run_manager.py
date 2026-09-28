"""RunManager: tracks AccountRunner instances per account."""
import asyncio
import logging

from backend.runner import AccountRunner

logger = logging.getLogger("fb_commenter")


class RunManager:
    def __init__(self):
        self._runners = {}  # name -> AccountRunner

    def get(self, name):
        return self._runners.get(name)

    async def start(self, account, mode, opts):
        name = account["name"]
        existing = self._runners.get(name)
        if existing and existing.status in ("starting", "running"):
            raise RuntimeError(f"Account {name} đang chạy")
        runner = AccountRunner(account, mode=mode, opts=opts)
        self._runners[name] = runner
        await runner.start()
        return runner.snapshot()

    async def stop(self, name):
        runner = self._runners.get(name)
        if not runner:
            return {"name": name, "status": "idle"}
        await runner.stop()
        return runner.snapshot()

    async def stop_all(self):
        await asyncio.gather(
            *(r.stop() for r in self._runners.values()),
            return_exceptions=True,
        )
        return self.status()

    def status(self):
        return {name: r.snapshot() for name, r in self._runners.items()}
