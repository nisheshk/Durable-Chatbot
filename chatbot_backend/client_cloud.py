#!/usr/bin/env python3

import asyncio
import sys
from typing import Optional
from temporalio.client import Client

from workflows.chat_workflow import SignalQueryOpenAIWorkflow
from config_cloud import cloud_config


class ChatbotCloudClient:
    """Cloud client for executing chatbot workflows."""
    
    def __init__(self):
        self.client: Optional[Client] = None
    
    async def connect(self) -> None:
        """Connect to Temporal Cloud."""
        if self.client:
            return
            
        try:
            cloud_config.validate()
            self.client = await Client.connect(**cloud_config.get_temporal_connection_config())
            print(f"✓ Connected to Temporal Cloud: {cloud_config.TEMPORAL_CLOUD_NAMESPACE}")
        except Exception as e:
            print(f"✗ Failed to connect to Temporal Cloud: {e}")
            raise
    
    async def send_message(self, session_id: str, message: str, user_id: int = None) -> str:
        """Send a message to a chatbot session."""
        if not self.client:
            await self.connect()
        
        # Use session_id directly as workflow_id (matches web UI format)
        workflow_id = session_id
        
        try:
            # Start workflow if it doesn't exist, or signal existing workflow
            await self.client.start_workflow(
                SignalQueryOpenAIWorkflow.run,
                args=[cloud_config.INACTIVITY_TIMEOUT_MINUTES, user_id],
                id=workflow_id,
                task_queue=cloud_config.TASK_QUEUE,
                start_signal="user_prompt",
                start_signal_args=[message],
            )
            return f"Message sent to session {session_id}: {message}"
            
        except Exception as e:
            print(f"✗ Error sending message to session {session_id}: {e}")
            raise
    
    async def get_conversation_history(self, session_id: str) -> list:
        """Get conversation history for a session."""
        if not self.client:
            await self.connect()
        
        # Use session_id directly as workflow_id (matches web UI format)
        workflow_id = session_id
        
        try:
            handle = self.client.get_workflow_handle(workflow_id)
            history = await handle.query(SignalQueryOpenAIWorkflow.get_conversation_history)
            return history
        except Exception as e:
            print(f"✗ Error getting history for session {session_id}: {e}")
            return []
    
    async def close(self) -> None:
        """Close the client connection."""
        if self.client:
            # Temporal client doesn't need explicit closing
            self.client = None


async def main():
    """Simple CLI interface for testing."""
    if len(sys.argv) < 3:
        print("Usage: python client_cloud.py <session_id> <message>")
        print("Example: python client_cloud.py 'test-session-1' 'Hello, how are you?'")
        return 1
    
    session_id = sys.argv[1]
    message = sys.argv[2]
    user_id = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    
    client = ChatbotCloudClient()
    
    try:
        # Send message
        result = await client.send_message(session_id, message, user_id)
        print(result)
        
        # Wait a moment for response
        print("⏳ Waiting for response...")
        await asyncio.sleep(25)
        
        # Get conversation history
        history = await client.get_conversation_history(session_id)
        print("\n📜 Conversation History:")
        for speaker, text in history:
            icon = "👤" if speaker == "user" else "🤖"
            print(f"{icon} {speaker.title()}: {text}")
        
        await client.close()
        return 0
        
    except Exception as e:
        print(f"✗ Client error: {e}")
        await client.close()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)