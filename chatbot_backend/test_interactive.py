#!/usr/bin/env python3
"""
Interactive test script for agent-based tool selection chatbot.

This script tests the new AI-powered tool selection system and provides
an interactive way to send messages and see responses with tool usage.

Usage:
    python test_interactive.py "your message here"  # Single message
    python test_interactive.py                      # Run test scenarios
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add chatbot_backend to path
sys.path.insert(0, str(Path(__file__).parent))

from client_cloud import ChatbotCloudClient
from config_cloud import cloud_config


async def send_message_to_workflow(session_id: str, message: str, timeout_minutes: int = 2, user_id: int = None):
    """Wrapper function to send message and get response with timeout."""
    client = ChatbotCloudClient()
    
    try:
        # Send message
        await client.send_message(session_id, message, user_id)
        
        # Wait for response with timeout
        max_retries = timeout_minutes * 12  # 5 second intervals
        for attempt in range(max_retries):
            await asyncio.sleep(5)  # Wait 5 seconds between checks
            
            # Get conversation history
            history = await client.get_conversation_history(session_id)
            
            # Check if we have a response to our message
            user_messages = [msg for speaker, msg in history if speaker == "user" and message in msg]
            response_messages = [msg for speaker, msg in history if speaker == "response"]
            
            if user_messages and len(response_messages) >= len(user_messages):
                # Return the latest response
                return response_messages[-1]
        
        # Timeout reached
        raise TimeoutError(f"No response received within {timeout_minutes} minutes")
        
    finally:
        await client.close()


async def test_agent_tool_selection():
    """Test the new agent-based tool selection with various scenarios."""
    
    print("🚀 Agent-Based Tool Selection Test")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"☁️ Using Temporal Cloud: {cloud_config.TEMPORAL_CLOUD_NAMESPACE}")
    print()
    
    session_id = "agent-test-session"
    
    # Test scenarios designed to test the new agent-based approach
    test_cases = [
        {
            "name": "Company Search - Direct Request",
            "message": "Find IT consulting companies in California",
            "expected": "Should trigger Databricks search for companies"
        },
        {
            "name": "Company Search - Natural Language",
            "message": "I need suppliers for cloud computing services",
            "expected": "Agent should understand this needs company search"
        },
        {
            "name": "Web Search - Current Information",
            "message": "What's the latest news about artificial intelligence?",
            "expected": "Should trigger web search for current info"
        },
        {
            "name": "Web Search - Real-time Data",
            "message": "What's Apple's stock price today?",
            "expected": "Agent should use web search for current data"
        },
        {
            "name": "Mixed Intent - Both Tools",
            "message": "Find current suppliers for the latest AI technology trends",
            "expected": "Agent might use both tools or intelligently choose one"
        },
        {
            "name": "Conversational - No Tools",
            "message": "Hello, how are you doing today?",
            "expected": "Agent should determine no tools are needed"
        },
        {
            "name": "Ambiguous Query",
            "message": "Tell me about Microsoft",
            "expected": "Agent decides between company info or current news"
        },
        {
            "name": "Complex Business Query",
            "message": "What construction companies in Texas have been in the news recently?",
            "expected": "Agent intelligently combines or chooses between tools"
        }
    ]
    
    print(f"🧪 Running {len(test_cases)} test scenarios:")
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. {test_case['name']}")
        print(f"   📝 Query: \"{test_case['message']}\"")
        print(f"   🎯 Expected: {test_case['expected']}")
        
        try:
            # Send message and get response
            response = await send_message_to_workflow(
                session_id, 
                test_case['message'], 
                timeout_minutes=2  # Longer timeout for tool execution
            )
            
            print(f"   ✅ Response received ({len(response)} chars)")
            
            # Analyze response to see what tools were used
            response_lower = response.lower()
            tools_detected = []
            
            # Check for databricks/company search usage
            if any(phrase in response_lower for phrase in [
                "databricks_search tool", "company search results", "companies found",
                "companies identified", "company information found"
            ]):
                tools_detected.append("🏢 Company Search")
            
            # Check for web search usage
            if any(phrase in response_lower for phrase in [
                "web_search tool", "current web information", "latest information",
                "current information:", "web search", "real-time"
            ]):
                tools_detected.append("🌐 Web Search")
            
            # Check for agent reasoning
            if any(phrase in response_lower for phrase in [
                "tool selection reasoning", "agent", "based on the user", 
                "the databricks_search tool", "the web_search tool"
            ]):
                tools_detected.append("🤖 Agent Selection")
            
            if tools_detected:
                print(f"   🛠️  Tools Used: {' + '.join(tools_detected)}")
            else:
                print("   💬 Standard Chat (No Tools)")
            
            # Show truncated response
            max_len = 200
            truncated_response = response[:max_len] + "..." if len(response) > max_len else response
            print(f"   💭 Response: {truncated_response}")
            
        except Exception as e:
            print(f"   ❌ Test failed: {str(e)}")
        
        print()  # Add spacing between tests
    
    print("🎉 Agent-Based Tool Selection Test Complete!")
    print()
    print("🔍 Analysis:")
    print("  • The AI agent now decides which tools to use contextually")
    print("  • No more rigid keyword matching - intelligent understanding")
    print("  • Tools can be combined or skipped based on query analysis")
    print("  • Tool selection reasoning is included in responses")
    print()
    print("💡 Next Steps:")
    print("  • Run test_scalability.py to test with multiple concurrent sessions")
    print("  • Monitor tool selection accuracy and adjust descriptors if needed")


async def interactive_chat():
    """Interactive chat mode for testing individual messages."""
    print("🗨️  Interactive Chat Mode")
    print("=" * 40)
    print("💡 Type your messages to test the agent-based tool selection")
    print("💡 The agent will decide whether to use tools based on context")
    print("💡 Press Ctrl+C to exit")
    print()
    
    session_id = f"interactive-{datetime.now().strftime('%H%M%S')}"
    message_count = 0
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            if not user_input:
                continue
            
            message_count += 1
            print(f"🤖 Processing message {message_count}...")
            
            # Send to chatbot
            response = await send_message_to_workflow(
                session_id,
                user_input,
                timeout_minutes=2
            )
            
            # Analyze and display response
            print("🤖 Assistant:", response)
            
            # Show tool analysis
            response_lower = response.lower()
            if "tool selection reasoning:" in response_lower:
                print("   🧠 Agent-based tool selection was used")
            
            print()  # Add spacing
            
        except KeyboardInterrupt:
            print("\n👋 Chat ended. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print()


async def send_single_message(message: str):
    """Send a single message and display the response."""
    print(f"📤 Sending message: \"{message}\"")
    print()
    
    try:
        # Use timestamp-based session ID for single messages
        session_id = f"single-{datetime.now().strftime('%H%M%S')}"
        
        response = await send_message_to_workflow(
            session_id,
            message,
            timeout_minutes=2
        )
        
        print("🤖 Response:")
        print("-" * 40)
        print(response)
        print("-" * 40)
        
        # Tool analysis
        response_lower = response.lower()
        tools_used = []
        
        # Check for databricks/company search usage
        if any(phrase in response_lower for phrase in [
            "databricks_search tool", "company search results", "companies found",
            "companies identified", "company information found"
        ]):
            tools_used.append("🏢 Company/Supplier Search")
        
        # Check for web search usage
        if any(phrase in response_lower for phrase in [
            "web_search tool", "current web information", "latest information",
            "current information:", "web search", "real-time"
        ]):
            tools_used.append("🌐 Real-time Web Search")
        
        # Check for agent reasoning
        if any(phrase in response_lower for phrase in [
            "tool selection reasoning", "agent", "based on the user", 
            "the databricks_search tool", "the web_search tool"
        ]):
            tools_used.append("🤖 Agent Decision Making")
        
        if tools_used:
            print(f"🛠️  Tools Used: {' • '.join(tools_used)}")
        else:
            print("💬 Standard chat response (no tools needed)")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def validate_environment():
    """Validate that the environment is properly configured."""
    print("🔧 Environment Validation")
    print("-" * 30)
    
    try:
        cloud_config.validate()
        print("✅ Cloud configuration validated")
        print(f"   • Temporal Cloud: {cloud_config.TEMPORAL_CLOUD_NAMESPACE}")
        print(f"   • Task Queue: {cloud_config.TASK_QUEUE}")
        print("✅ OpenAI API configured")
        print("✅ Databricks credentials configured")
        print()
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print()
        print("💡 Make sure:")
        print("   • OPENAI_API_KEY is set in your environment")
        print("   • Databricks credentials are configured")
        print("   • Temporal Cloud connection is working")
        print("   • Worker is running: python worker_cloud.py")
        return False


if __name__ == "__main__":
    # Validate environment first
    if not asyncio.run(validate_environment()):
        sys.exit(1)
    
    if len(sys.argv) > 1:
        # Single message mode
        message = " ".join(sys.argv[1:])
        asyncio.run(send_single_message(message))
    else:
        # Show menu
        print("🎯 Choose test mode:")
        print("1. Run predefined test scenarios (recommended)")
        print("2. Interactive chat mode")
        print()
        
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "2":
            asyncio.run(interactive_chat())
        else:
            # Default to test scenarios
            asyncio.run(test_agent_tool_selection())