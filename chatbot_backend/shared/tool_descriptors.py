"""
Tool descriptor system for agent-based tool selection.

This module defines the available tools and their capabilities in a self-describing format
that can be used by AI agents to make intelligent tool selection decisions.
"""

from typing import List, Dict, Any
from .models import ToolDescriptor, ToolType


def get_databricks_search_descriptor() -> ToolDescriptor:
    """Get the descriptor for the Databricks company search tool."""
    return ToolDescriptor(
        tool_type=ToolType.DATABRICKS_SEARCH,
        name="Company & Supplier Database Search",
        description=(
            "Searches a comprehensive database of companies and suppliers using vector similarity search. "
            "Returns detailed company information including contact details, capabilities, locations, "
            "and scope of work. Ideal for finding suppliers, vendors, contractors, and business partners "
            "based on business requirements, location, industry, or specific capabilities."
        ),
        use_cases=[
            "Finding suppliers for specific products or services",
            "Locating companies with particular capabilities or expertise", 
            "Searching for vendors in specific geographic regions",
            "Identifying contractors for construction or IT projects",
            "Getting contact information for business partners",
            "Finding companies that match specific procurement requirements",
            "Researching competitors or market players in an industry",
            "Locating certified or qualified service providers"
        ],
        input_schema={
            "type": "object",
            "properties": {
                "query_text": {
                    "type": "string",
                    "description": "Natural language search query describing the company or supplier requirements"
                },
                "num_results": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of results to return (1-20)"
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["company_name", "city", "state", "phone", "website", "email", "capability", "scope_of_work_ranges"],
                    "description": "Specific data fields to retrieve"
                }
            },
            "required": ["query_text"]
        },
        example_queries=[
            "Find IT companies in Texas that provide cloud services",
            "I need construction contractors in California",
            "Search for suppliers that manufacture medical devices",
            "Find companies that provide logistics services in the Midwest",
            "Look for software development firms with AI expertise",
            "I need vendors for renewable energy projects",
            "Find certified minority-owned businesses in New York",
            "Search for companies with expertise in aerospace engineering"
        ]
    )


def get_web_search_descriptor() -> ToolDescriptor:
    """Get the descriptor for the web search tool."""
    return ToolDescriptor(
        tool_type=ToolType.WEB_SEARCH,
        name="Real-time Web Search",
        description=(
            "Performs real-time web searches to find current information, news, trends, and up-to-date data "
            "from across the internet. Uses advanced AI to analyze and summarize search results, providing "
            "comprehensive and current information on any topic. Ideal for getting the latest news, current "
            "prices, recent developments, or any information that changes frequently."
        ),
        use_cases=[
            "Getting current news and breaking stories",
            "Finding latest stock prices or market information",
            "Checking current weather conditions",
            "Researching recent developments in technology or industry",
            "Finding trending topics or viral content",
            "Getting up-to-date product information or reviews",
            "Checking current prices for goods or services",
            "Finding recent research or scientific publications",
            "Getting current sports scores or statistics",
            "Finding real-time traffic or transportation information"
        ],
        input_schema={
            "type": "object", 
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for finding current/real-time information"
                }
            },
            "required": ["query"]
        },
        example_queries=[
            "What's the current stock price of Apple?",
            "Latest news about artificial intelligence breakthroughs",
            "Current weather in San Francisco",
            "What's trending on social media today?",
            "Recent developments in electric vehicle technology",
            "Current cryptocurrency prices",
            "Latest sports scores from NBA games",
            "Breaking news in the technology sector",
            "Current interest rates for mortgages",
            "What's happening in the stock market right now?"
        ]
    )


def get_all_tool_descriptors() -> List[ToolDescriptor]:
    """Get all available tool descriptors."""
    return [
        get_databricks_search_descriptor(),
        get_web_search_descriptor()
    ]


def get_tool_descriptor_by_type(tool_type: ToolType) -> ToolDescriptor:
    """Get a specific tool descriptor by type."""
    descriptors = {desc.tool_type: desc for desc in get_all_tool_descriptors()}
    if tool_type not in descriptors:
        raise ValueError(f"Unknown tool type: {tool_type}")
    return descriptors[tool_type]


def format_tools_for_agent(tools: List[ToolDescriptor]) -> str:
    """Format tool descriptors for agent consumption."""
    formatted_tools = []
    
    for i, tool in enumerate(tools, 1):
        tool_info = f"""
Tool {i}: {tool.name} ({tool.tool_type.value})
Description: {tool.description}

Key Use Cases:
{chr(10).join(f"- {use_case}" for use_case in tool.use_cases[:5])}

Example Queries:
{chr(10).join(f'- "{example}"' for example in tool.example_queries[:3])}
"""
        formatted_tools.append(tool_info.strip())
    
    return "\n\n" + "="*80 + "\n\n".join(formatted_tools)