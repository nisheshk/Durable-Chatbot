#!/usr/bin/env python3

import asyncio
import concurrent.futures
import logging
import sys
from temporalio.client import Client
from temporalio.worker import Worker

from workflows.chat_workflow import SignalQueryOpenAIWorkflow
from activities.openai_activities import (
    OpenAIActivities,
    databricks_search_company_info,
    web_search_realtime_info
)
from activities.agent_tool_selection import select_tools_for_query
from config_cloud import cloud_config


async def main():
    """Run the Temporal Cloud worker for chatbot."""
    
    # Validate cloud configuration
    try:
        cloud_config.validate()
        print("✓ Cloud configuration validated")
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
        return 1
    
    # Connect to Temporal Cloud
    try:
        client = await Client.connect(**cloud_config.get_temporal_connection_config())
        print(f"✓ Connected to Temporal Cloud: {cloud_config.TEMPORAL_CLOUD_NAMESPACE}")
    except Exception as e:
        print(f"✗ Failed to connect to Temporal Cloud: {e}")
        return 1
    
    # Initialize activities
    activities = OpenAIActivities()
    
    # Create thread pool for activity execution
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=cloud_config.MAX_CONCURRENT_ACTIVITY_TASKS
    ) as activity_executor:
        
        # Create and configure worker with scaling settings
        worker = Worker(
            client,
            task_queue=cloud_config.TASK_QUEUE,
            workflows=[SignalQueryOpenAIWorkflow],
            activities=[
                activities.prompt_openai,
                activities.save_conversation_to_db,
                databricks_search_company_info,
                web_search_realtime_info,
                select_tools_for_query
            ],
            activity_executor=activity_executor,
            # Scaling configuration from cloud config
            max_concurrent_activities=cloud_config.MAX_CONCURRENT_ACTIVITIES,
            max_concurrent_workflow_tasks=cloud_config.MAX_CONCURRENT_WORKFLOW_TASKS,
        )
        
        print(f"✓ Worker created for task queue: {cloud_config.TASK_QUEUE}")
        print(f"✓ Scaling config: {cloud_config.MAX_CONCURRENT_ACTIVITIES} activities, "
              f"{cloud_config.MAX_CONCURRENT_WORKFLOW_TASKS} workflow tasks")
        print("🚀 Starting cloud worker...")
        
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
    
    # Suppress noisy temporal logs in production
    logging.getLogger('temporalio').setLevel(logging.WARNING)
    
    # Run worker and exit with proper code
    exit_code = asyncio.run(main())
    sys.exit(exit_code)