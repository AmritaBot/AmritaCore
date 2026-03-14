import asyncio

from amrita_core import create_agent


async def minimal_example():
    # Create an agent with minimal parameters
    agent = create_agent(
        url="YOUR_API_ENDPOINT",  # Replace with your API endpoint
        key="YOUR_API_KEY",  # Replace with your API key
        model_config={"model": "gpt-3.5-turbo", "stream": True},
    )

    # Get a chat object for the interaction
    chat = agent.get_chatobject("Hello, what can you do?")

    # Execute the interaction and get the response
    async with chat.begin():
        print(await chat.full_response())


# Run the example
if __name__ == "__main__":
    asyncio.run(minimal_example())
