"""AccountRunner: runs one Facebook account job (uid or campaign) as an asyncio task."""
import asyncio
import logging
from pathlib import Path

from facebook_fanpage_commenter import FacebookFanpageCommenter
from campaign_run import run_campaign

BASE_DIR = Path(__file__).resolve().parents[1]
PARENT_DIR = BASE_DIR.parents[1]  # "tool cmt"


class AccountRunner:
    """One account + one run configuration -> one asyncio.Task."""

    def __init__(self, account, mode="uid", opts=None, log=None):
        self.account = dict(account)
        self.name = self.account.get("name", "?")
        self.mode = mode
        self.opts = dict(opts or {})
        self.status = "idle"  # idle|starting|running|stopping|done|error
        self.error = ""
        self.task = None
        self._commenter = None
        self._cookie_tmp = None
        self.log = log or logging.getLogger("fb_commenter")

    async def start(self):
        if self.task and not self.task.done():
            raise RuntimeError(f"Account {self.name} đang chạy")
        self.status = "starting"
        self.error = ""
        self.task = asyncio.create_task(self._run(), name=f"run:{self.name}")
        return self.task

    async def stop(self):
        self.status = "stopping"
        if self._commenter:
            try:
                await self._commenter.close_browser()
            except Exception:
                pass
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except (asyncio.CancelledError, Exception):
                pass
        self.status = "idle"

    def snapshot(self):
        return {
            "name": self.name,
            "mode": self.mode,
            "status": self.status,
            "error": self.error,
        }

    def _cookie_path(self):
        """Resolve a cookies file path for the commenter (dummy when cookies_text set)."""
        return Path(self.account.get("cookie_file") or BASE_DIR / "cookies.txt")

    def _build_commenter(self):
        opts = self.opts
        comment_list = self.account.get("comment_list") or str(
            PARENT_DIR / "comments" / "comment list.txt"
        )
        profile_dir = ""
        if self.account.get("use_profile"):
            raw = self.account.get("profile_dir") or ""
            profile_dir = raw or str(BASE_DIR / "data" / "profiles" / self.name)
        self._commenter = FacebookFanpageCommenter(
            urls=opts.get("urls", ""),
            cookies_file=str(self._cookie_path()),
            cookies_text=(self.account.get("cookie") or "").strip() or None,
            comment_file=comment_list,
            page_id=self.account.get("page_id", ""),
            proxy=None if opts.get("no_proxy") else self.account.get("proxy") or None,
            delay_min=int(opts.get("delay_min", 1)),
            delay_max=int(opts.get("delay_max", 60)),
            headless=bool(opts.get("headless", False)),
            require_proxy=not opts.get("no_proxy", False),
            user_data_dir=profile_dir or None,
            account_name=self.name,
        )
        return self._commenter

    async def _run(self):
        try:
            commenter = self._build_commenter()
            self.status = "running"
            if self.mode == "campaign":
                await run_campaign(
                    commenter,
                    PARENT_DIR,
                    self.opts.get("campaign", ""),
                    dry_run=bool(self.opts.get("dry_run", False)),
                    cooldown_seconds=self.opts.get("cooldown"),
                    account_name=self.name,
                )
            else:
                await commenter.run()
            self.status = "done"
        except asyncio.CancelledError:
            self.status = "idle"
            raise
        except Exception as exc:
            self.status = "error"
            self.error = str(exc)[:400]
            self.log.exception("Run %s failed", self.name)
        finally:
            self._commenter = None
