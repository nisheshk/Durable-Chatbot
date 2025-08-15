import os
import psycopg2
from psycopg2 import pool
from typing import List, Tuple, Dict, Any, Optional
from temporalio import activity
from openai import OpenAI
from databricks.vector_search.client import VectorSearchClient
from config_cloud import cloud_config
from shared.models import (
    DatabricksSearchRequest, 
    DatabricksSearchResponse, 
    WebSearchRequest, 
    WebSearchResponse
)

# Global connection pool - shared across all activity instances
_connection_pool = None


def get_connection_pool():
    """Get or create the global connection pool."""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=50,  # 5 workers × 10 connections each
                dsn=cloud_config.DATABASE_URL,
                connection_factory=None
            )
            activity.logger.info("Database connection pool created successfully")
        except Exception as e:
            activity.logger.error(f"Failed to create connection pool: {str(e)}")
            raise
    return _connection_pool


class OpenAIActivities:
    def __init__(self) -> None:
        # Use cloud configuration for API keys and settings
        if not cloud_config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = OpenAI(api_key=cloud_config.OPENAI_API_KEY)
        
        # Initialize connection pool
        self.connection_pool = get_connection_pool()

    @activity.defn
    def prompt_openai(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=cloud_config.MAX_TOKENS,
                temperature=cloud_config.TEMPERATURE,
                top_p=cloud_config.TOP_P,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            activity.logger.error(f"Error in OpenAI chat completion: {str(e)}")
            raise
    
    @activity.defn
    def save_conversation_to_db(self, user_id: Optional[int], conversation_history: List[Tuple[str, str]], summary: str = None) -> bool:
        conn = None
        try:
            # Get connection from pool instead of creating new one
            conn = self.connection_pool.getconn()
            cur = conn.cursor()
            
            # Use workflow_id from Temporal context - it will be the session ID
            workflow_id = activity.info().workflow_id
            
            # Use the actual user_id passed to the workflow
            db_user_id = user_id
            
            # OPTIMIZED: Use UPSERT instead of DELETE + INSERT
            # This eliminates the need for DELETE and handles duplicates automatically
            if conversation_history:
                # First, clear existing conversation for this workflow_id (still needed for order consistency)
                cur.execute("DELETE FROM public.conversations WHERE workflow_id = %s", (workflow_id,))
                
                # Handle user_id being None for testing
                if db_user_id is not None:
                    # Batch insert with user_id
                    conversation_data = [
                        (workflow_id, speaker, message, order, db_user_id) 
                        for order, (speaker, message) in enumerate(conversation_history)
                    ]
                    cur.executemany("""
                        INSERT INTO public.conversations (workflow_id, speaker, message, message_order, user_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, conversation_data)
                else:
                    # Batch insert without user_id for testing
                    conversation_data = [
                        (workflow_id, speaker, message, order) 
                        for order, (speaker, message) in enumerate(conversation_history)
                    ]
                    cur.executemany("""
                        INSERT INTO public.conversations (workflow_id, speaker, message, message_order)
                        VALUES (%s, %s, %s, %s)
                    """, conversation_data)
            
            # Save summary if provided (using UPSERT)
            if summary:
                if db_user_id is not None:
                    cur.execute("""
                        INSERT INTO public.conversation_summaries (workflow_id, summary, user_id)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (workflow_id) DO UPDATE SET 
                            summary = EXCLUDED.summary,
                            updated_at = CURRENT_TIMESTAMP
                    """, (workflow_id, summary, db_user_id))
                else:
                    # Insert summary without user_id for testing
                    cur.execute("""
                        INSERT INTO public.conversation_summaries (workflow_id, summary)
                        VALUES (%s, %s)
                        ON CONFLICT (workflow_id) DO UPDATE SET 
                            summary = EXCLUDED.summary,
                            updated_at = CURRENT_TIMESTAMP
                    """, (workflow_id, summary))
            
            conn.commit()
            cur.close()
            
            activity.logger.info(f"Saved conversation for workflow {workflow_id} to database")
            return True
            
        except Exception as e:
            activity.logger.error(f"Error saving conversation to database: {str(e)}")
            raise
        finally:
            # Return connection to pool instead of closing
            if conn:
                self.connection_pool.putconn(conn)


class DatabricksVectorClient:
    """Client for Databricks vector search operations."""
    
    def __init__(self, host: str, token: str):
        self.host = host.rstrip('/')
        self.token = token
        self.vector_search_client = VectorSearchClient(
            workspace_url=host,
            personal_access_token=token
        )
    
    def similarity_search(self, 
                         index_name: str,
                         endpoint_name: str,
                         query_text: str,
                         num_results: int = 10,
                         filters: Dict[str, Any] = None,
                         columns: List[str] = None) -> Dict[str, Any]:
        """Perform similarity search on a Databricks vector search index."""
        
        if not endpoint_name:
            raise ValueError("endpoint_name is required")
        if not index_name:
            raise ValueError("index_name is required")
        if not query_text:
            raise ValueError("query_text is required")
        
        # Get the vector search index
        vector_search_index = self.vector_search_client.get_index(
            endpoint_name=endpoint_name,
            index_name=index_name,
        )
        
        activity.logger.info(f"Searching endpoint: {endpoint_name}, index: {index_name}")
        activity.logger.info(f"Query: {query_text}, Results: {num_results}")
        
        # Perform similarity search
        results = vector_search_index.similarity_search(
            query_text=query_text,
            columns=columns,
            filters=filters,
            num_results=num_results,
            query_type="ann",
        )
        
        # Convert results to dictionary format
        raw_results = results.as_dict() if hasattr(results, 'as_dict') else results
        
        # Sort results by data comprehensiveness
        sorted_results = self._sort_results_by_comprehensiveness(raw_results)
        
        return sorted_results
    
    def _calculate_data_comprehensiveness(self, row_data: List, columns: List[str]) -> float:
        """Calculate a comprehensiveness score for a company record."""
        if len(row_data) != len(columns):
            return 0.0
        
        score = 0.0
        data_dict = dict(zip(columns, row_data))
        
        # Weight different types of data
        weights = {
            'contact_info': 3.0,    # phone, email, website
            'address_info': 2.0,    # city, state, address  
            'business_info': 3.0,   # capability, scope_of_work_ranges
            'basic_info': 1.0       # company_name, etc.
        }
        
        # Contact information fields
        contact_fields = ['phone', 'email', 'website']
        contact_score = sum(1 for field in contact_fields 
                          if data_dict.get(field) and str(data_dict[field]).strip())
        score += (contact_score / len(contact_fields)) * weights['contact_info']
        
        # Address information fields  
        address_fields = ['city', 'state', 'physical_address', 'address', 'zip']
        available_address_fields = [f for f in address_fields if f in columns]
        if available_address_fields:
            address_score = sum(1 for field in available_address_fields
                              if data_dict.get(field) and str(data_dict[field]).strip())
            score += (address_score / len(available_address_fields)) * weights['address_info']
        
        # Business information fields
        business_fields = ['capability', 'scope_of_work_ranges', 'commodity_codes']
        available_business_fields = [f for f in business_fields if f in columns]
        if available_business_fields:
            business_score = sum(1 for field in available_business_fields
                               if data_dict.get(field) and str(data_dict[field]).strip())
            score += (business_score / len(available_business_fields)) * weights['business_info']
        
        # Basic information - company name is required
        if data_dict.get('company_name') and str(data_dict['company_name']).strip():
            score += weights['basic_info']
        
        return min(score, 10.0)  # Cap at 10.0
    
    def _sort_results_by_comprehensiveness(self, search_results: Dict[str, Any]) -> Dict[str, Any]:
        """Sort search results by data comprehensiveness."""
        try:
            if not isinstance(search_results, dict):
                return search_results
                
            # Handle different response formats
            if 'result' in search_results and 'data_array' in search_results['result']:
                data_array = search_results['result']['data_array']
                columns = search_results['result'].get('manifest', {}).get('schema', {}).get('column_names', [])
                
                if not columns or not data_array:
                    return search_results
                
                # Calculate comprehensiveness for each row
                enhanced_results = []
                for row in data_array:
                    score = self._calculate_data_comprehensiveness(row, columns)
                    enhanced_results.append({
                        'data': row,
                        'comprehensiveness_score': score
                    })
                
                # Sort by comprehensiveness score (descending)
                enhanced_results.sort(key=lambda x: x['comprehensiveness_score'], reverse=True)
                
                # Return sorted results
                return {
                    'result': {
                        'data_array': [item['data'] for item in enhanced_results],
                        'manifest': search_results['result'].get('manifest', {}),
                    },
                    'sorted_by_comprehensiveness': True,
                    'total_results': len(enhanced_results),
                    'comprehensiveness_scores': [item['comprehensiveness_score'] for item in enhanced_results]
                }
            
            return search_results
            
        except Exception as e:
            activity.logger.error(f"Error sorting results by comprehensiveness: {str(e)}")
            return search_results


@activity.defn
async def databricks_search_company_info(request: DatabricksSearchRequest) -> DatabricksSearchResponse:
    """
    Temporal activity to perform Databricks vector search for company information.
    """
    
    try:
        # Get Databricks configuration from cloud config
        databricks_host = cloud_config.DATABRICKS_HOST
        databricks_token = cloud_config.DATABRICKS_TOKEN
        databricks_endpoint = cloud_config.DATABRICKS_ENDPOINT_NAME
        databricks_index = cloud_config.DATABRICKS_INDEX_NAME
        
        if not databricks_host or not databricks_token:
            raise ValueError("DATABRICKS_HOST and DATABRICKS_TOKEN must be configured in cloud config")
        
        # Use cloud config or fall back to request parameters
        endpoint_name = databricks_endpoint or request.endpoint_name
        index_name = databricks_index or request.index_name
        
        activity.logger.info(f"Starting Databricks company search for query: {request.query_text}")
        
        # Initialize the Databricks Vector client
        client = DatabricksVectorClient(databricks_host, databricks_token)
        
        # Perform the similarity search
        result = client.similarity_search(
            index_name=index_name,
            endpoint_name=endpoint_name,
            query_text=request.query_text,
            num_results=request.num_results,
            filters=request.filters,
            columns=request.columns
        )
        
        activity.logger.info(f"Databricks company search completed. Found {result.get('total_results', 0)} results")
        
        # Extract data from result
        if 'result' in result and 'data_array' in result['result']:
            data_array = result['result']['data_array']
            manifest = result['result'].get('manifest', {})
            columns = manifest.get('schema', {}).get('column_names', request.columns or [])
        else:
            data_array = []
            columns = request.columns or []
        
        return DatabricksSearchResponse(
            data_array=data_array,
            columns=columns,
            total_results=len(data_array),
            comprehensiveness_scores=result.get('comprehensiveness_scores')
        )
        
    except Exception as e:
        activity.logger.error(f"Error in Databricks company search: {str(e)}")
        raise


@activity.defn
async def web_search_realtime_info(request: WebSearchRequest) -> WebSearchResponse:
    """
    Temporal activity to perform web search for real-time information.
    """
    
    try:
        # Use cloud config for OpenAI API key
        if not cloud_config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be configured in cloud config")
        
        activity.logger.info(f"Starting web search for query: {request.query}")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=cloud_config.OPENAI_API_KEY)
        
        # Prepare the search prompt
        search_prompt = f"""Please search the web for current information about: {request.query}

Provide up to {request.max_results} relevant results and then give a comprehensive summary of the findings. Focus on the most recent and accurate information available."""

        # Use GPT-4o-search-preview for web search
        response = client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[
                {
                    "role": "user",
                    "content": search_prompt
                }
            ],
            max_tokens=2048,
        )
        
        # Extract the response content
        search_content = response.choices[0].message.content
        
        activity.logger.info(f"Web search completed for query: {request.query}")
        
        # Create result structure
        results = [
            {
                "title": f"Web Search Results for: {request.query}",
                "content": search_content,
                "source": "OpenAI GPT-4o Search Preview",
                "timestamp": "current"
            }
        ]
        
        return WebSearchResponse(
            query=request.query,
            results=results,
            summary=search_content,
            total_results=len(results)
        )
        
    except Exception as e:
        activity.logger.error(f"Error in web search: {str(e)}")
        raise
