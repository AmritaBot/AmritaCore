from unittest.mock import MagicMock

import pytest

from amrita_core.tools.manager import (
    MultiToolsManager,
    ToolsManager,
    _parse_google_docstring,
    _python_type_to_json_type,
    on_tools,
    simple_tool,
)
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    ToolData,
    ToolFunctionSchema,
)


class TestMultiToolsManager:
    @pytest.fixture
    def manager(self) -> MultiToolsManager:
        manager = MultiToolsManager()
        manager._models = {}
        manager._disabled_tools = set()
        return manager

    def test_initialization(self):
        manager = MultiToolsManager()
        assert manager._models == {}
        assert manager._disabled_tools == set()

    def test_has_tool(self, manager: MultiToolsManager):
        assert not manager.has_tool("nonexistent_tool")

        tool_data = MagicMock()
        tool_data.data.function.name = "test_tool"
        manager.register_tool(tool_data)

        assert manager.has_tool("test_tool")
        assert not manager.has_tool("other_tool")

    def test_register_and_get_tool(self, manager: MultiToolsManager):
        func_mock = MagicMock()
        func_mock.return_value = "test result"

        function_def = FunctionDefinitionSchema(
            name="test_tool",
            description="Test tool description",
            parameters=FunctionParametersSchema(type="object", properties={}),
        )

        tool_data = ToolData(
            func=func_mock,
            data=ToolFunctionSchema(
                function=function_def, type="function", strict=False
            ),
        )

        manager.register_tool(tool_data)

        retrieved_tool = manager.get_tool("test_tool")
        assert retrieved_tool is not None
        assert retrieved_tool == tool_data
        assert retrieved_tool.func == func_mock

        assert manager.get_tool("nonexistent_tool") is None
        assert manager.get_tool("nonexistent_tool", "default") == "default"

    def test_remove_tool(self, manager: MultiToolsManager):
        tool_data = MagicMock()
        tool_data.data.function.name = "test_tool"
        manager.register_tool(tool_data)

        assert manager.has_tool("test_tool")

        manager.remove_tool("test_tool")

        assert not manager.has_tool("test_tool")

    def test_disable_enable_tool(self, manager: MultiToolsManager):
        tool_data = MagicMock()
        tool_data.data.function.name = "test_tool"
        manager.register_tool(tool_data)

        assert manager.has_tool("test_tool")
        assert manager.get_tool("test_tool") is not None

        manager.disable_tool("test_tool")

        assert not manager.has_tool("test_tool")
        assert manager.get_tool("test_tool") is None

        manager.enable_tool("test_tool")

        assert manager.has_tool("test_tool")
        assert manager.get_tool("test_tool") is not None

    def test_get_disabled_tools(self, manager: MultiToolsManager):
        tool_data = MagicMock()
        tool_data.data.function.name = "test_tool"
        manager.register_tool(tool_data)

        manager.disable_tool("test_tool")

        disabled_tools = manager.get_disabled_tools()
        assert "test_tool" in disabled_tools

    def test_get_tools_and_meta(self, manager: MultiToolsManager):
        tool_data = MagicMock()
        tool_data.data.function.name = "test_tool"
        manager.register_tool(tool_data)

        tools = manager.get_tools()
        assert "test_tool" in tools
        assert tools["test_tool"] == tool_data

        meta = manager.tools_meta()
        assert "test_tool" in meta

        meta_dict = manager.tools_meta_dict()
        assert "test_tool" in meta_dict


class TestToolsManagerSingleton:
    def test_singleton_behavior(self):
        manager1 = ToolsManager()
        manager2 = ToolsManager()
        assert manager1 is manager2

        tool_data = MagicMock()
        tool_data.data.function.name = "shared_tool"
        manager1.register_tool(tool_data)

        assert manager2.has_tool("shared_tool")


def test_parse_google_docstring():
    def sample_function():
        """This is a sample function.

        Args:
            param1 (int): The first parameter.
            param2 (str): The second parameter.

        Returns:
            bool: The return value.
        """
        pass

    desc, params = _parse_google_docstring(sample_function.__doc__)

    assert "This is a sample function" in desc
    assert "param1" in params
    assert "param2" in params
    assert params["param1"] == "The first parameter."
    assert params["param2"] == "The second parameter."


def test_python_type_to_json_type():
    assert _python_type_to_json_type(str) == "string"
    assert _python_type_to_json_type(int) == "integer"
    assert _python_type_to_json_type(float) == "number"
    assert _python_type_to_json_type(bool) == "boolean"
    assert _python_type_to_json_type(list) == "array"
    assert _python_type_to_json_type(dict) == "object"

    assert _python_type_to_json_type(type) == "string"


def test_on_tools_decorator():
    function_def = FunctionDefinitionSchema(
        name="decorated_tool",
        description="A decorated tool",
        parameters=FunctionParametersSchema(type="object", properties={}),
    )

    @on_tools(function_def)
    async def test_function(params):
        return "result"

    manager = ToolsManager()
    tool = manager.get_tool("decorated_tool")
    assert tool is not None
    assert tool.data.function.name == "decorated_tool"

    manager.remove_tool("decorated_tool")


@pytest.mark.asyncio
async def test_simple_tool_decorator():
    @simple_tool
    def add_numbers(a: int, b: int) -> int:
        """Add two numbers together.

        Args:
            a (int): The first number.
            b (int): The second number.

        Returns:
            int: The sum of the two numbers.
        """
        return a + b

    manager = ToolsManager()
    tool = manager.get_tool("add_numbers")

    if tool is not None:
        result = await tool.func({"a": 5, "b": 3})  # type: ignore
        assert result == "8"

    manager.remove_tool("add_numbers")


def test_tool_data_access_methods():
    manager = MultiToolsManager()

    func_mock = MagicMock()
    function_def = FunctionDefinitionSchema(
        name="test_method_tool",
        description="Test tool for method access",
        parameters=FunctionParametersSchema(type="object", properties={}),
    )

    tool_data = ToolData(
        func=func_mock,
        data=ToolFunctionSchema(function=function_def, type="function", strict=False),
        custom_run=False,
    )

    manager.register_tool(tool_data)

    assert manager.get_tool_meta("test_method_tool") is not None
    assert manager.get_tool_func("test_method_tool") is not None

    assert manager.get_tool("nonexistent", "default") == "default"
    assert manager.get_tool_meta("nonexistent", "default") == "default"
    assert manager.get_tool_func("nonexistent", "default") == "default"

    manager.remove_tool("test_method_tool")
