import asyncio

import pytest

from amrita_core.streaming import SuspendObjectStream


@pytest.mark.asyncio
async def test_chatobject_suspend_tags():
    obj = SuspendObjectStream()
    suspend = False

    async def suspend_func():
        nonlocal suspend
        while True:
            if await obj._wait_for_continue():
                pytest.fail("Should not continue without correct tag")
            elif await obj._wait_for_continue("test-tag"):
                break
        suspend = True

    hd: asyncio.Task[None] = asyncio.create_task(suspend_func())
    try:
        await obj.wait_to_suspend("test-tag", timeout=2)
        obj.resume()
        await asyncio.wait_for(hd, 0.2)
        assert suspend, "Suspend not called"
    finally:
        hd.cancel()


@pytest.mark.asyncio
async def test_chatobject_suspend():
    obj = SuspendObjectStream()
    suspend = False

    async def suspend_func():
        nonlocal suspend
        while True:
            if await obj._wait_for_continue():
                break
        suspend = True

    hd: asyncio.Task[None] = asyncio.create_task(suspend_func())
    try:
        await obj.wait_to_suspend(timeout=2)
        obj.resume()
        await asyncio.wait_for(hd, 0.2)
        assert suspend, "Suspend not called"
    finally:
        hd.cancel()
