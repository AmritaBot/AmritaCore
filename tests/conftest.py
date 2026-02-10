import sys
from pathlib import Path

import pytest
from pytest_asyncio import is_async_test

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_collection_modifyitems(items: list[pytest.Item]):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)
    from amrita_core import init

    init()
