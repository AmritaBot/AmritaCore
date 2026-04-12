import asyncio

import pytest

from amrita_core.threadsafe import ContextThreadsafe


@pytest.mark.asyncio
async def test_thread_safe() -> None:
    ctx = type("TestCTX", (ContextThreadsafe,), {})()
    await asyncio.wait_for(ctx.__aenter__(), timeout=1)
    await asyncio.wait_for(ctx.__aexit__(None, None, None), timeout=1)


async def acquire_and_hold(
    ctx, acquired_event: asyncio.Event, release_event: asyncio.Event
):
    try:
        await ctx.__aenter__()
        acquired_event.set()
        await release_event.wait()
        await ctx.__aexit__(None, None, None)
    except Exception:
        try:
            await ctx.__aexit__(None, None, None)
        except Exception:
            pass


@pytest.mark.asyncio
async def test_lock_conflict() -> None:
    ctx = type("TestCTX", (ContextThreadsafe,), {})()

    acquired_event = asyncio.Event()
    release_event = asyncio.Event()
    holder_task = asyncio.create_task(
        acquire_and_hold(ctx, acquired_event, release_event)
    )
    await asyncio.wait_for(acquired_event.wait(), timeout=1)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(ctx.__aenter__(), timeout=0.1)
    release_event.set()
    await asyncio.wait_for(holder_task, timeout=1)
    await asyncio.wait_for(ctx.__aenter__(), timeout=0.1)
    await asyncio.wait_for(ctx.__aexit__(None, None, None), timeout=0.1)
