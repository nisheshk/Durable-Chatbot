import os
from typing import Optional
from dotenv import load_dotenv

# Load cloud environment variables
load_dotenv('.env.cloud')


class CloudConfig:
    """Configuration for Temporal Cloud deployment of chatbot."""
    
    # Temporal Cloud Configuration
    TEMPORAL_CLOUD_NAMESPACE: str = os.getenv("TEMPORAL_CLOUD_NAMESPACE", "")
    TEMPORAL_CLOUD_ADDRESS: str = os.getenv("TEMPORAL_CLOUD_ADDRESS", "")
    TEMPORAL_CLOUD_API_KEY: str = os.getenv("TEMPORAL_CLOUD_API_KEY", "")
    
    # Database Configuration (Neon PostgreSQL)
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Databricks Configuration
    DATABRICKS_HOST: str = os.getenv("DATABRICKS_HOST", "")
    DATABRICKS_TOKEN: str = os.getenv("DATABRICKS_TOKEN", "")
    DATABRICKS_ENDPOINT_NAME: str = os.getenv("DATABRICKS_ENDPOINT_NAME", "")
    DATABRICKS_INDEX_NAME: str = os.getenv("DATABRICKS_INDEX_NAME", "")
    
    # Chatbot Configuration
    INACTIVITY_TIMEOUT_MINUTES: int = int(os.getenv("INACTIVITY_TIMEOUT_MINUTES", "5"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "512"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.1"))
    TOP_P: float = float(os.getenv("TOP_P", "0.2"))
    
    # Task Queue Configuration
    TASK_QUEUE: str = "chatbot-cloud-task-queue"
    
    # Worker Scaling Configuration
    MAX_CONCURRENT_ACTIVITIES: int = int(os.getenv("MAX_CONCURRENT_ACTIVITIES", "20"))
    MAX_CONCURRENT_WORKFLOW_TASKS: int = int(os.getenv("MAX_CONCURRENT_WORKFLOW_TASKS", "10"))
    MAX_CONCURRENT_ACTIVITY_TASKS: int = int(os.getenv("MAX_CONCURRENT_ACTIVITY_TASKS", "20"))
    
    # Database Connection Pool Settings
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "30"))
    
    @classmethod
    def validate(cls) -> None:
        """Validate that required cloud configuration is present."""
        required_vars = [
            ("TEMPORAL_CLOUD_NAMESPACE", cls.TEMPORAL_CLOUD_NAMESPACE),
            ("TEMPORAL_CLOUD_ADDRESS", cls.TEMPORAL_CLOUD_ADDRESS),
            ("TEMPORAL_CLOUD_API_KEY", cls.TEMPORAL_CLOUD_API_KEY),
            ("DATABASE_URL", cls.DATABASE_URL),
            ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
        ]
        
        missing = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing.append(var_name)
        
        if missing:
            raise ValueError(f"Missing required cloud environment variables: {', '.join(missing)}")
    
    @classmethod
    def get_temporal_connection_config(cls) -> dict:
        """Get Temporal Cloud connection configuration."""
        from temporalio.client import TLSConfig
        
        return {
            "target_host": cls.TEMPORAL_CLOUD_ADDRESS,
            "namespace": cls.TEMPORAL_CLOUD_NAMESPACE,
            "tls": TLSConfig(),
            "rpc_metadata": {
                "temporal-namespace": cls.TEMPORAL_CLOUD_NAMESPACE,
                "authorization": f"Bearer {cls.TEMPORAL_CLOUD_API_KEY}"
            }
        }


# Global cloud config instance
cloud_config = CloudConfig()