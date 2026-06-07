"""
MCP (Model Context Protocol) Integration Example for AmritaCore

This example demonstrates how to integrate MCP clients with AmritaCore
to extend agent capabilities with external tools and data sources.
"""

import asyncio

from amrita_core import create_agent, minimal_init
from amrita_core.config import AmritaConfig, FunctionConfig


async def mcp_integration_example():
    """Demonstrate MCP client integration"""
    print("🔌 MCP Integration Example")
    print("-" * 30)

    # Configure MCP scripts (these would be actual MCP script paths in real usage)
    mcp_scripts = [
        "./mcp-scripts/weather.mcp",
        "./mcp-scripts/database.mcp",
        "./mcp-scripts/calendar.mcp",
    ]

    # Create configuration with MCP enabled
    config = AmritaConfig(
        function_config=FunctionConfig(
            agent_mcp_client_enable=True,
            agent_mcp_server_scripts=mcp_scripts,
        )
    )

    # Create an agent with MCP support
    await minimal_init(config)
    agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-4",
        model_config={"temperature": 0.7, "stream": True},
    )

    print("💬 Starting conversation with MCP-enabled agent:")
    print()

    # Test weather query (would use weather.mcp script)
    weather_input = "What's the weather like in New York today?"

    print(f"👤 User: {weather_input}")
    print("🤖 Assistant: ", end="")

    chat = agent.get_chatobject(weather_input)

    async with chat.begin():
        async for message in chat.io_stream.get_response_generator():
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")

    print("\n")

    # Test database query (would use database.mcp script)
    db_input = "Query our customer database for users in California."

    print(f"👤 User: {db_input}")
    print("🤖 Assistant: ", end="")

    chat2 = agent.get_chatobject(db_input)

    async with chat2.begin():
        async for message in chat2.io_stream.get_response_generator():
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")

    print("\n")
    print("✅ MCP integration example completed!")

    # Note: In a real implementation, you would need to:
    # 1. Have actual MCP scripts in the specified paths
    # 2. Ensure the MCP client manager is properly initialized
    # 3. Handle MCP client lifecycle management


# Alternative example showing manual MCP client setup
async def manual_mcp_setup():
    """Demonstrate manual MCP client setup"""
    print("\n🔧 Manual MCP Client Setup")
    print("-" * 30)

    try:
        from amrita_core.tools import mcp

        # Initialize MCP clients manually
        client_manager = mcp.ClientManager()
        scripts = ["/path/to/your/script1.mcp", "/path/to/your/script2.mcp"]

        # This would initialize the scripts (commented out as paths may not exist)
        await client_manager.initialize_scripts_all(scripts)

        print("MCP clients initialized successfully!")
        print("Available scripts:", scripts)

    except ImportError:
        print("MCP module not available - skipping manual setup example")
    except Exception as e:
        print(f"MCP setup failed: {e}")


if __name__ == "__main__":
    # Run the main example
    asyncio.run(mcp_integration_example())

    # Run manual setup example
    asyncio.run(manual_mcp_setup())
