import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from backend.runner import AccountRunner


def _account():
    return {
        "name": "acc1", "cookie": "c_user=1; xs=2", "page_id": "123",
        "proxy": "", "profile_dir": "", "comment_list": "", "use_profile": 0,
    }


@pytest.mark.asyncio
async def test_runner_uid_success(tmp_path):
    runner = AccountRunner(_account(), mode="uid", opts={})
    fake = AsyncMock()
    fake.run = AsyncMock()
    fake.close_browser = AsyncMock()
    with patch.object(runner, "_build_commenter", return_value=fake):
        await runner.start()
        await runner.task
    assert runner.status == "done"
    fake.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_runner_error_status(tmp_path):
    runner = AccountRunner(_account(), mode="uid", opts={})
    fake = AsyncMock()
    fake.run = AsyncMock(side_effect=RuntimeError("boom"))
    fake.close_browser = AsyncMock()
    with patch.object(runner, "_build_commenter", return_value=fake):
        await runner.start()
        await runner.task
    assert runner.status == "error"
    assert "boom" in runner.error


@pytest.mark.asyncio
async def test_runner_stop_cancels(tmp_path):
    runner = AccountRunner(_account(), mode="uid", opts={})
    fake = AsyncMock()

    async def hang():
        await asyncio.sleep(60)

    fake.run = hang
    fake.close_browser = AsyncMock()
    with patch.object(runner, "_build_commenter", return_value=fake):
        await runner.start()
        await asyncio.sleep(0.05)
        await runner.stop()
    assert runner.status == "idle"
