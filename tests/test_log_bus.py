import asyncio
import logging

import pytest

from backend.log_bus import LogBus


@pytest.mark.asyncio
async def test_subscribe_receives_matching_account():
    bus = LogBus()
    logger = logging.getLogger("test.bus")
    logger.addHandler(bus)
    logger.setLevel(logging.INFO)

    received = []

    async def collect():
        async for entry in bus.subscribe("acc1"):
            received.append(entry)
            if len(received) >= 1:
                return

    task = asyncio.create_task(collect())
    await asyncio.sleep(0)

    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello acc1", None, None)
    record.account = "acc1"
    bus.emit(record)
    record2 = logging.LogRecord("t", logging.INFO, __file__, 1, "other", None, None)
    record2.account = "acc2"
    bus.emit(record2)

    await asyncio.wait_for(task, 2)
    assert received[0]["account"] == "acc1"
    assert received[0]["msg"].endswith("hello acc1")
    logger.removeHandler(bus)


@pytest.mark.asyncio
async def test_wildcard_gets_all_and_scrubs_secrets():
    bus = LogBus()
    entries = []

    async def collect():
        async for e in bus.subscribe("*"):
            entries.append(e)
            if len(entries) >= 1:
                return

    task = asyncio.create_task(collect())
    await asyncio.sleep(0)
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "cookie xs=ABC123", None, None)
    record.account = "a"
    bus.emit(record)
    await asyncio.wait_for(task, 2)
    assert "ABC123" not in entries[0]["msg"]
    assert "<redacted>" in entries[0]["msg"]
