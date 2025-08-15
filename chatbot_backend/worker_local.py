#!/usr/bin/env python3

import asyncio
import concurrent.futures
import logging
import sys
import os
from temporalio.client import Client
from temporalio.worker import Worker

from workflows.chat_workflow import SignalQueryOpenAIWorkflow
from activities.openai_activities import (
    OpenAIActivities,
    databricks_search_company_info,
    web_search_realtime_info
)
from activities.agent_tool_selection import select_tools_for_query


# Local development configuration
class LocalConfig:
    TEMPORAL_HOST = "localhost"
    TEMPORAL_PORT = 7233
    TASK_QUEUE = "chatbot-task-queue"
    
    # Default scaling settings for local development
    MAX_CONCURRENT_ACTIVITIES = 5
    MAX_CONCURRENT_WORKFLOW_TASKS = 5
    MAX_CONCURRENT_ACTIVITY_TASKS = 5
    
    def get_temporal_connection_config(self):
        return {
            "target_host": f"{self.TEMPORAL_HOST}:{self.TEMPORAL_PORT}",
        }


async def main():
    """Run the local Temporal worker for chatbot."""
    
    local_config = LocalConfig()
    
    # Check required environment variables
    required_env_vars = ["OPENAI_API_KEY", "DATABASE_URL"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"✗ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file or export them directly")
        return 1
    
    print("✓ Required environment variables found")
    
    # Connect to local Temporal server
    try:
        client = await Client.connect(**local_config.get_temporal_connection_config())
        print(f"✓ Connected to local Temporal server: {local_config.TEMPORAL_HOST}:{local_config.TEMPORAL_PORT}")
    except Exception as e:
        print(f"✗ Failed to connect to local Temporal server: {e}")
        print("Make sure to start the local server with: temporal server start-dev")
        return 1
    
    # Initialize activities
    activities = OpenAIActivities()
    
    # Create thread pool for activity execution
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=local_config.MAX_CONCURRENT_ACTIVITY_TASKS
    ) as activity_executor:
        
        # Create and configure worker with scaling settings
        worker = Worker(
            client,
            task_queue=local_config.TASK_QUEUE,
            workflows=[SignalQueryOpenAIWorkflow],
            activities=[
                activities.prompt_openai,
                activities.save_conversation_to_db,
                databricks_search_company_info,
                web_search_realtime_info,
                select_tools_for_query
            ],
            activity_executor=activity_executor,
            # Scaling configuration for local development
            max_concurrent_activities=local_config.MAX_CONCURRENT_ACTIVITIES,
            max_concurrent_workflow_tasks=local_config.MAX_CONCURRENT_WORKFLOW_TASKS,
        )
        
        print(f"✓ Worker created for task queue: {local_config.TASK_QUEUE}")
        print(f"✓ Scaling config: {local_config.MAX_CONCURRENT_ACTIVITIES} activities, "
              f"{local_config.MAX_CONCURRENT_WORKFLOW_TASKS} workflow tasks")
        print("🚀 Starting local worker...")
        
        # Start the worker
        try:
            await worker.run()
        except KeyboardInterrupt:
            print("\n🛑 Worker shutting down...")
        except Exception as e:
            print(f"✗ Worker error: {e}")
            return 1
    
    return 0


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Allow more verbose logging for local development
    logging.getLogger('temporalio').setLevel(logging.INFO)
    
    # Run worker and exit with proper code
    exit_code = asyncio.run(main())
    sys.exit(exit_code)