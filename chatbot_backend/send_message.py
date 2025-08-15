import asyncio
import sys
import os
from pathlib import Path

# Add both parent directory and chatbot_backend to Python path
parent_path = str(Path(__file__).parent.parent.parent)
backend_path = str(Path(__file__).parent.parent.parent / "chatbot_backend")
sys.path.insert(0, parent_path)
sys.path.insert(0, backend_path)

from temporalio.client import Client
from workflows.chat_workflow import SignalQueryOpenAIWorkflow
from config_cloud import cloud_config


async def main(workflow_id, prompt, user_id):
    # Validate cloud configuration
    cloud_config.validate()
    
    # Create client connected to Temporal Cloud
    client = await Client.connect(**cloud_config.get_temporal_connection_config())

    # Sends a signal to the workflow (and starts it if needed)
    await client.start_workflow(
        SignalQueryOpenAIWorkflow.run,
        args=[cloud_config.INACTIVITY_TIMEOUT_MINUTES, user_id],
        id=workflow_id,
        task_queue=cloud_config.TASK_QUEUE,
        start_signal="user_prompt",
        start_signal_args=[prompt],
    )


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python send_message.py '<workflow_id>' '<prompt>' '<user_id>'")
        print("Example: python send_message.py 'session-1' 'What animals are marsupials?' '123'")
    else:
        asyncio.run(main(sys.argv[1], sys.argv[2], int(sys.argv[3])))