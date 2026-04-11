import asyncio

import pytest

from amrita_core.threadsafe import ContextThreadsafe


@pytest.mark.asyncio
async def test_thread_safe() -> None:
    ctx = type("TestCTX", (ContextThreadsafe,), {})()
    await asyncio.wait_for(ctx.__aenter__(), timeout=1)
    await asyncio.wait_for(ctx.__aexit__(None, None, None), timeout=1)


@pytest.mark.asyncio
async def test_lock_conflict() -> None:
    ctx = type("TestCTX", (ContextThreadsafe,), {})()
    await asyncio.wait_for(ctx.__aenter__(), timeout=1)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(ctx.__aenter__(), timeout=0.1)
    await asyncio.wait_for(ctx.__aexit__(None, None, None), timeout=1)
