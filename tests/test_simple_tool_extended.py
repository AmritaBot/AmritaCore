# pyright: reportOperatorIssue=false, reportOptionalMemberAccess=false


import pytest
from pydantic import BaseModel

from amrita_core.tools.manager import ToolsManager, simple_tool


# Test Pydantic model
class User(BaseModel):
    name: str
    age: int
    email: str | None = None


class Address(BaseModel):
    street: str
    city: str
    user: User  # Nested Pydantic model


class ContactInfo(BaseModel):
    phone: str
    address: Address


class TestSimpleToolExtended:
    """Test extended simple_tool functionality with Pydantic models and containers"""

    def setup_method(self):
        """Clean up ToolsManager state before each test"""
        manager = ToolsManager()
        # Clear all registered tools
        for tool_name in list(manager._models.keys()):
            manager.remove_tool(tool_name)

    def teardown_method(self):
        """Clean up ToolsManager state after each test"""
        manager = ToolsManager()
        # Clear all registered tools
        for tool_name in list(manager._models.keys()):
            manager.remove_tool(tool_name)

    def test_pydantic_model_parameter(self):
        """Test that Pydantic models work as parameters"""

        @simple_tool
        def process_user(user: User) -> str:
            """Process a user object."""
            return f"Processed user {user.name}"

        manager = ToolsManager()
        assert manager.has_tool("process_user")
        tool_meta = manager.get_tool_meta("process_user")
        params = tool_meta.function.parameters

        # The function has one parameter named "user"
        assert params.type == "object"
        assert "user" in params.properties
        assert params.required == ["user"]  # The parameter itself is required

        # The "user" parameter should be an object with User model properties
        user_prop = params.properties["user"]
        assert user_prop.type == "object"
        assert "name" in user_prop.properties
        assert "age" in user_prop.properties
        assert user_prop.required == ["name", "age"]

    def test_nested_pydantic_model(self):
        """Test nested Pydantic models"""

        @simple_tool
        def process_address(address: Address) -> str:
            """Process an address with nested user."""
            return f"Processed address for {address.user.name}"

        manager = ToolsManager()
        assert manager.has_tool("process_address")
        tool_meta = manager.get_tool_meta("process_address")
        params = tool_meta.function.parameters

        # The function has one parameter named "address"
        assert params.type == "object"
        assert "address" in params.properties
        assert params.required == ["address"]

        # The "address" parameter should be an object with Address model properties
        address_prop = params.properties["address"]
        assert address_prop.type == "object"
        assert "street" in address_prop.properties
        assert "city" in address_prop.properties
        assert "user" in address_prop.properties
        assert address_prop.required == ["street", "city", "user"]

        # Check nested user properties
        assert address_prop.properties
        user_prop = address_prop.properties["user"]
        assert user_prop.type == "object"
        assert "name" in user_prop.properties
        assert "age" in user_prop.properties

    def test_list_of_pydantic_models(self):
        """Test List[PydanticModel] parameter"""

        @simple_tool
        def process_users(users: list[User]) -> str:
            """Process multiple users."""
            return f"Processed {len(users)} users"

        manager = ToolsManager()
        assert manager.has_tool("process_users")
        tool_meta = manager.get_tool_meta("process_users")
        params = tool_meta.function.parameters

        # The function has one parameter named "users"
        assert params.type == "object"
        assert "users" in params.properties
        assert params.required == ["users"]

        users_prop = params.properties["users"]
        assert users_prop.type == "array"
        assert users_prop.items is not None
        assert users_prop.items.type == "object"
        assert "name" in users_prop.items.properties

    def test_optional_pydantic_model_with_default(self):
        """Test Optional[PydanticModel] parameter WITH default value"""

        @simple_tool
        def process_optional_user(user: User | None = None) -> str:
            """Process an optional user with default None."""
            if user is None:
                return "No user provided"
            return f"Processed optional user {user.name}"

        manager = ToolsManager()
        assert manager.has_tool("process_optional_user")
        tool_meta = manager.get_tool_meta("process_optional_user")
        params = tool_meta.function.parameters

        # The function has one parameter named "user"
        assert params.type == "object"
        assert "user" in params.properties

        # With default value, the parameter should NOT be required
        assert "user" not in (params.required or [])

        user_prop = params.properties["user"]
        assert user_prop.type == "object"
        assert "name" in user_prop.properties
        assert "age" in user_prop.properties

    def test_list_of_basic_types(self):
        """Test List[str] parameter"""

        @simple_tool
        def process_string_list(items: list[str]) -> str:
            """Process a list of strings."""
            return f"Processed {len(items)} strings"

        manager = ToolsManager()
        assert manager.has_tool("process_string_list")
        tool_meta = manager.get_tool_meta("process_string_list")
        params = tool_meta.function.parameters

        # The function has one parameter named "items"
        assert params.type == "object"
        assert "items" in params.properties
        assert params.required == ["items"]

        items_prop = params.properties["items"]
        assert items_prop.type == "array"
        assert items_prop.items is not None
        assert items_prop.items.type == "string"

    def test_dict_type_rejected(self):
        """Test that Dict types are rejected"""
        with pytest.raises(ValueError, match="Dict types are not supported"):

            @simple_tool
            def process_dict_data(data: dict[str, str]) -> str:
                """This should fail."""
                return "Should not reach here"

    def test_nested_containers_rejected(self):
        """Test that nested containers are rejected"""
        with pytest.raises(ValueError, match="Nested containers are not allowed"):

            @simple_tool
            def process_nested_list(items: list[list[str]]) -> str:
                """This should fail."""
                return "Should not reach here"

    def test_any_type_rejected(self):
        """Test that Any type is rejected"""
        from typing import Any

        with pytest.raises(ValueError, match=r"Any.*not allowed"):

            @simple_tool
            def process_any_data(data: Any) -> str:
                """This should fail."""
                return "Should not reach here"

    def test_empty_list_parameter(self):
        """Test that empty lists are handled correctly"""

        @simple_tool
        def process_empty_list(items: list[str]) -> str:
            """Process a potentially empty list."""
            if not items:
                return "Empty list"
            return f"Processed {len(items)} items"

        manager = ToolsManager()
        assert manager.has_tool("process_empty_list")
        tool_meta = manager.get_tool_meta("process_empty_list")
        params = tool_meta.function.parameters

        assert params.type == "object"
        assert "items" in params.properties
        assert params.required == ["items"]

        items_prop = params.properties["items"]
        assert items_prop.type == "array"
        assert items_prop.items.type == "string"

    def test_complex_nested_model(self):
        """Test deeply nested Pydantic models"""

        @simple_tool
        def process_contact(contact: ContactInfo) -> str:
            """Process contact info with deep nesting."""
            return f"Contact: {contact.phone}, {contact.address.city}"

        manager = ToolsManager()
        assert manager.has_tool("process_contact")
        tool_meta = manager.get_tool_meta("process_contact")
        params = tool_meta.function.parameters

        assert params.type == "object"
        assert "contact" in params.properties
        assert params.required == ["contact"]

        contact_prop = params.properties["contact"]
        assert contact_prop.type == "object"
        assert "phone" in contact_prop.properties
        assert "address" in contact_prop.properties

        # Check nested address
        assert contact_prop.properties
        address_prop = contact_prop.properties["address"]
        assert address_prop.type == "object"
        assert "street" in address_prop.properties
        assert "city" in address_prop.properties
        assert "user" in address_prop.properties

        # Check deeply nested user
        assert address_prop.properties
        user_prop = address_prop.properties["user"]
        assert user_prop.type == "object"
        assert "name" in user_prop.properties
        assert "age" in user_prop.properties

    def test_union_type_rejected(self):
        """Test that Union types (other than Optional) are rejected"""
        with pytest.raises(
            ValueError,
            match=r"Union types with multiple non-None types are not supported.*",
        ):

            @simple_tool
            def process_union_data(data: str | int) -> str:
                """This should fail."""
                return "Should not reach here"

    def test_no_parameters_function(self):
        """Test function with no parameters"""

        @simple_tool
        def get_current_time() -> str:
            """Get current time with no parameters."""
            return "Current time"

        manager = ToolsManager()
        assert manager.has_tool("get_current_time")
        tool_meta = manager.get_tool_meta("get_current_time")
        params = tool_meta.function.parameters

        assert params.type == "object"
        assert params.properties == {}  # Empty properties
        assert params.required == []  # No required parameters

    def test_multiple_parameters_mixed_types(self):
        """Test function with multiple parameters of mixed types"""

        @simple_tool
        def process_mixed_data(user: User, tags: list[str], debug: bool = False) -> str:
            """Process mixed parameter types."""
            return f"User: {user.name}, Tags: {len(tags)}, Debug: {debug}"

        manager = ToolsManager()
        assert manager.has_tool("process_mixed_data")
        tool_meta = manager.get_tool_meta("process_mixed_data")
        params = tool_meta.function.parameters

        assert params.type == "object"
        assert "user" in params.properties
        assert "tags" in params.properties
        assert "debug" in params.properties

        # Required parameters (no default values)
        assert "user" in params.required
        assert "tags" in params.required
        # Optional parameter (has default value)
        assert "debug" not in params.required

        # Check individual parameter types
        assert params.properties["user"].type == "object"
        assert params.properties["tags"].type == "array"
        assert params.properties["tags"].items.type == "string"
        assert params.properties["debug"].type == "boolean"


def test_simple_tool_reject_no_typehint():
    with pytest.raises(RuntimeError):

        @simple_tool
        def testa(a): ...
