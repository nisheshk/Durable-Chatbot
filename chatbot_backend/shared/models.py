from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class DatabricksSearchRequest(BaseModel):
    """Request for Databricks vector search."""
    
    endpoint_name: str = Field(description="Databricks vector search endpoint")
    index_name: str = Field(description="Vector search index name")
    query_text: str = Field(description="Search query text")
    num_results: int = Field(default=10, description="Number of results to return")
    columns: Optional[List[str]] = Field(default=None, description="Columns to retrieve")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional search filters")


class DatabricksSearchResponse(BaseModel):
    """Response from Databricks vector search."""
    
    data_array: List[List[Any]] = Field(description="Raw search results data")
    columns: List[str] = Field(description="Column names for data")
    total_results: int = Field(description="Number of results returned")
    comprehensiveness_scores: Optional[List[float]] = Field(
        default=None, 
        description="Data comprehensiveness scores"
    )


class WebSearchRequest(BaseModel):
    """Request for web search."""
    
    query: str = Field(description="Search query text")
    max_results: int = Field(default=10, description="Maximum number of results to return")
    location: Optional[Dict[str, Any]] = Field(default=None, description="Optional location context for search")


class WebSearchResponse(BaseModel):
    """Response from web search."""
    
    query: str = Field(description="Original search query")
    results: List[Dict[str, Any]] = Field(description="Web search results")
    summary: str = Field(description="AI-generated summary of the search results")
    total_results: int = Field(description="Number of results found")


class CompanyInfo(BaseModel):
    """Structured company information from Databricks search."""
    
    company_name: str = Field(description="Company name")
    phone: Optional[str] = Field(default=None, description="Phone number")
    email: Optional[str] = Field(default=None, description="Email address")
    website: Optional[str] = Field(default=None, description="Website URL")
    city: Optional[str] = Field(default=None, description="City")
    state: Optional[str] = Field(default=None, description="State")
    address: Optional[str] = Field(default=None, description="Physical address")
    zip_code: Optional[str] = Field(default=None, description="ZIP code")
    capability: Optional[str] = Field(default=None, description="Business capabilities")
    scope_of_work: Optional[str] = Field(default=None, description="Scope of work ranges")
    commodity_codes: Optional[str] = Field(default=None, description="Commodity codes")
    comprehensiveness_score: Optional[float] = Field(default=None, description="Data quality score")


class ToolType(str, Enum):
    """Available tool types."""
    DATABRICKS_SEARCH = "databricks_search"
    WEB_SEARCH = "web_search"


class ToolDescriptor(BaseModel):
    """Self-describing tool capabilities."""
    
    tool_type: ToolType = Field(description="Type of tool")
    name: str = Field(description="Human-readable tool name")
    description: str = Field(description="Detailed description of what the tool does")
    use_cases: List[str] = Field(description="List of specific use cases for this tool")
    input_schema: Dict[str, Any] = Field(description="JSON schema for tool input")
    example_queries: List[str] = Field(description="Example user queries that would trigger this tool")


class ToolSelection(BaseModel):
    """Agent's tool selection decision."""
    
    tool_type: ToolType = Field(description="Selected tool type")
    confidence: float = Field(description="Confidence score (0.0-1.0)")
    reasoning: str = Field(description="Why this tool was selected")
    parameters: Dict[str, Any] = Field(description="Parameters to pass to the tool")


class AgentToolSelectionRequest(BaseModel):
    """Request for agent-based tool selection."""
    
    user_query: str = Field(description="User's query/message")
    conversation_context: Optional[str] = Field(default=None, description="Recent conversation context")
    available_tools: List[ToolDescriptor] = Field(description="Available tools and their capabilities")


class AgentToolSelectionResponse(BaseModel):
    """Response from agent-based tool selection."""
    
    selected_tools: List[ToolSelection] = Field(description="Tools selected by the agent")
    reasoning: str = Field(description="Overall reasoning for tool selection decisions")
    should_use_tools: bool = Field(description="Whether any tools should be used")
    confidence_score: float = Field(description="Overall confidence in the selection")