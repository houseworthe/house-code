"""
Test Phase 2: Core loop functionality

This tests that the core loop is working without actually calling the API.
"""

from house_code.core import HouseCode, ConversationContext, Message


def test_conversation_context():
    """Test that conversation context works."""
    context = ConversationContext()

    # Add messages
    context.add_message("user", "Hello")
    context.add_message("assistant", "Hi there!")

    # Check messages
    assert len(context.messages) == 2
    assert context.messages[0].role == "user"
    assert context.messages[1].role == "assistant"

    # Check API format
    api_messages = context.get_messages_for_api()
    assert len(api_messages) == 2
    assert api_messages[0]["role"] == "user"
    assert api_messages[0]["content"] == "Hello"

    print("✅ ConversationContext works!")


def test_tool_registration():
    """Test that tools can be registered."""
    agent = HouseCode(api_key="test-key", model="test-model")

    # Define a simple test tool
    tool_def = {
        "name": "test_tool",
        "description": "A test tool",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"]
        }
    }

    def test_executor(message: str) -> str:
        return f"Executed with: {message}"

    # Register tool
    agent.register_tool(tool_def, test_executor)

    # Check it's registered
    assert len(agent.tools) == 1
    assert agent.tools[0]["name"] == "test_tool"
    assert "test_tool" in agent.tool_executors

    # Test execution
    result = agent._execute_tool("test_tool", {"message": "hello"})
    assert result == "Executed with: hello"

    print("✅ Tool registration works!")


def test_system_prompt():
    """Test that system prompt is generated."""
    agent = HouseCode(api_key="test-key")
    prompt = agent._build_system_prompt()

    # Check for key elements from introspection
    assert "House Code" in prompt
    assert "Read before Edit" in prompt
    assert "tool" in prompt.lower()

    print("✅ System prompt generation works!")


def test_garbage_collection_detection():
    """Test that garbage collection threshold is detected."""
    agent = HouseCode(api_key="test-key")

    # Add lots of messages to exceed threshold (150k tokens)
    # ~4 chars per token, so need 600k+ chars
    for i in range(700):
        agent.context.add_message("user", "x" * 1000)

    # Should need GC
    assert agent.needs_garbage_collection()

    print("✅ Garbage collection detection works!")


if __name__ == "__main__":
    print("Testing Phase 2: Core Loop\n")

    test_conversation_context()
    test_tool_registration()
    test_system_prompt()
    test_garbage_collection_detection()

    print("\n✅ Phase 2 core functionality verified!")
    print("\nTo test with real API:")
    print("  export ANTHROPIC_API_KEY=your-key")
    print('  /Users/ethanhouseworth/Documents/Personal-Projects/house-code/venv/bin/house "create a hello world Python script"')
