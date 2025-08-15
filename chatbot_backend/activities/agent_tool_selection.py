"""
Agent-based tool selection activity for intelligent tool recommendation.

This module provides AI-powered tool selection that replaces rigid keyword-based
intent detection with contextual, intelligent decision making.
"""

import json
from typing import List, Dict, Any
from temporalio import activity
from openai import AsyncOpenAI
from config_cloud import cloud_config
from shared.models import (
    AgentToolSelectionRequest,
    AgentToolSelectionResponse, 
    ToolSelection,
    ToolType,
    ToolDescriptor
)
from shared.tool_descriptors import format_tools_for_agent


class AgentToolSelectionActivity:
    """Activity for agent-based tool selection."""
    
    def __init__(self):
        if not cloud_config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = AsyncOpenAI(api_key=cloud_config.OPENAI_API_KEY)
    
    @activity.defn
    async def select_tools_for_query(self, request) -> AgentToolSelectionResponse:
        """
        Use AI agent to intelligently select appropriate tools for a user query.
        
        Args:
            request: Tool selection request containing user query and available tools (dict or AgentToolSelectionRequest)
            
        Returns:
            Tool selection response with selected tools and reasoning
        """
        try:
            activity.logger.info(f"Received request type: {type(request)}")
            if hasattr(request, '__dict__'):
                activity.logger.info(f"Request attributes: {list(request.__dict__.keys())}")
            elif isinstance(request, dict):
                activity.logger.info(f"Request keys: {list(request.keys())}")
            
            # Handle both dict and object types from Temporal
            if isinstance(request, dict):
                # Check if this is a Temporal context dict (contains activity_id, etc.)
                if 'activity_id' in request or 'workflow_id' in request:
                    activity.logger.error(f"ERROR: Received Temporal context instead of request data!")
                    activity.logger.error(f"This suggests the activity method signature or calling convention is incorrect.")
                    # Return empty selection rather than crash
                    return AgentToolSelectionResponse(
                        selected_tools=[],
                        reasoning="Activity received invalid data format - Temporal context instead of request",
                        should_use_tools=False,
                        confidence_score=0.0
                    )
                
                user_query = request.get('user_query', '')
                conversation_context = request.get('conversation_context')
                available_tools = request.get('available_tools', [])
                # Convert dict tool descriptors back to objects if needed
                if available_tools and isinstance(available_tools[0], dict):
                    from shared.tool_descriptors import get_all_tool_descriptors
                    available_tools = get_all_tool_descriptors()  # Use fresh instances
            else:
                user_query = request.user_query
                conversation_context = request.conversation_context
                available_tools = request.available_tools
            
            activity.logger.info(f"Agent tool selection for query: {user_query}")
            
            # Format tools for agent consumption
            tools_description = format_tools_for_agent(available_tools)
            
            # Create the agent prompt
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(user_query, conversation_context, tools_description)
            
            # Call OpenAI to get tool selection decisions
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
                temperature=0.1,  # Low temperature for consistent decisions
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            response_content = response.choices[0].message.content
            parsed_response = json.loads(response_content)
            
            activity.logger.info(f"Agent selected {len(parsed_response.get('selected_tools', []))} tools")
            
            # Convert to structured response
            return self._parse_agent_response(parsed_response, request.available_tools)
            
        except Exception as e:
            activity.logger.error(f"Error in agent tool selection: {str(e)}")
            # Return empty selection on error
            return AgentToolSelectionResponse(
                selected_tools=[],
                reasoning=f"Tool selection failed due to error: {str(e)}",
                should_use_tools=False,
                confidence_score=0.0
            )
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent."""
        return """You are an intelligent tool selection agent. Your job is to analyze user queries and determine which tools (if any) should be used to provide the best response.

IMPORTANT INSTRUCTIONS:
1. You must respond with valid JSON only
2. Be conservative - only select tools when they would genuinely improve the response
3. Consider the user's intent carefully - don't over-interpret simple conversational messages
4. For each selected tool, provide clear reasoning and appropriate parameters
5. If no tools are needed, set should_use_tools to false

RESPONSE FORMAT (JSON):
{
  "should_use_tools": boolean,
  "selected_tools": [
    {
      "tool_type": "databricks_search" | "web_search",
      "confidence": float (0.0-1.0),
      "reasoning": "Clear explanation of why this tool was selected",
      "parameters": {
        "query_text": "search query" (for databricks_search),
        "query": "search query" (for web_search),  
        "num_results": integer (for databricks_search only)
      }
    }
  ],
  "reasoning": "Overall explanation of tool selection decisions",
  "confidence_score": float (0.0-1.0)
}

DECISION CRITERIA:
- Use databricks_search for: company/supplier/vendor lookups, business directory searches, finding service providers
- Use web_search for: current events, real-time information, recent news, market data, trending topics
- Use both tools when query requires both company data AND current information
- Use no tools for: general conversation, simple questions that don't require external data

Be precise and only select tools that will meaningfully improve the response quality."""
    
    def _create_user_prompt(self, user_query: str, conversation_context: str, tools_description: str) -> str:
        """Create the user prompt with query and available tools."""
        context_section = ""
        if conversation_context:
            context_section = f"\n\nCONVERSATION CONTEXT:\n{conversation_context}\n"
        
        return f"""USER QUERY: "{user_query}"{context_section}

AVAILABLE TOOLS:{tools_description}

Analyze the user query and determine which tools (if any) should be used. Respond with JSON only."""
    
    def _parse_agent_response(self, parsed_response: Dict[str, Any], available_tools: List[ToolDescriptor]) -> AgentToolSelectionResponse:
        """Parse the agent's JSON response into structured format."""
        try:
            # Create tool type mapping for validation
            valid_tool_types = {tool.tool_type.value: tool.tool_type for tool in available_tools}
            
            selected_tools = []
            for tool_data in parsed_response.get("selected_tools", []):
                tool_type_str = tool_data.get("tool_type")
                
                # Validate tool type
                if tool_type_str not in valid_tool_types:
                    activity.logger.warning(f"Invalid tool type selected: {tool_type_str}")
                    continue
                
                # Create tool selection
                tool_selection = ToolSelection(
                    tool_type=valid_tool_types[tool_type_str],
                    confidence=max(0.0, min(1.0, float(tool_data.get("confidence", 0.0)))),
                    reasoning=tool_data.get("reasoning", "No reasoning provided"),
                    parameters=tool_data.get("parameters", {})
                )
                selected_tools.append(tool_selection)
            
            return AgentToolSelectionResponse(
                selected_tools=selected_tools,
                reasoning=parsed_response.get("reasoning", "No overall reasoning provided"),
                should_use_tools=bool(parsed_response.get("should_use_tools", False)),
                confidence_score=max(0.0, min(1.0, float(parsed_response.get("confidence_score", 0.0))))
            )
            
        except Exception as e:
            activity.logger.error(f"Error parsing agent response: {str(e)}")
            return AgentToolSelectionResponse(
                selected_tools=[],
                reasoning=f"Failed to parse agent response: {str(e)}",
                should_use_tools=False,
                confidence_score=0.0
            )


# Create a simple function-based activity instead of class-based
@activity.defn
async def select_tools_for_query(request) -> AgentToolSelectionResponse:
    """
    Standalone function for agent-based tool selection.
    
    Args:
        request: Tool selection request (dict or AgentToolSelectionRequest)
        
    Returns:
        Tool selection response with selected tools and reasoning
    """
    try:
        activity.logger.info(f"[STANDALONE] Received request type: {type(request)}")
        if hasattr(request, '__dict__'):
            activity.logger.info(f"[STANDALONE] Request attributes: {list(request.__dict__.keys())}")
        elif isinstance(request, dict):
            activity.logger.info(f"[STANDALONE] Request keys: {list(request.keys())}")
        
        # Handle both dict and object types from Temporal
        if isinstance(request, dict):
            # Check if this is a Temporal context dict (contains activity_id, etc.)
            if 'activity_id' in request or 'workflow_id' in request:
                activity.logger.error(f"[STANDALONE] ERROR: Received Temporal context instead of request data!")
                activity.logger.error(f"[STANDALONE] This suggests the activity method signature or calling convention is incorrect.")
                # Return empty selection rather than crash
                return AgentToolSelectionResponse(
                    selected_tools=[],
                    reasoning="Activity received invalid data format - Temporal context instead of request",
                    should_use_tools=False,
                    confidence_score=0.0
                )
            
            user_query = request.get('user_query', '')
            conversation_context = request.get('conversation_context')
            available_tools = request.get('available_tools', [])
            # Convert dict tool descriptors back to objects if needed
            if available_tools and isinstance(available_tools[0], dict):
                from shared.tool_descriptors import get_all_tool_descriptors
                available_tools = get_all_tool_descriptors()  # Use fresh instances
        else:
            user_query = request.user_query
            conversation_context = request.conversation_context
            available_tools = request.available_tools
        
        activity.logger.info(f"[STANDALONE] Agent tool selection for query: {user_query}")
        
        # Initialize OpenAI client
        if not cloud_config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        client = AsyncOpenAI(api_key=cloud_config.OPENAI_API_KEY)
        
        # Format tools for agent consumption
        tools_description = format_tools_for_agent(available_tools)
        
        # Create the agent prompt
        system_prompt = _create_system_prompt()
        user_prompt = _create_user_prompt(user_query, conversation_context, tools_description)
        
        # Use OpenAI structured outputs with Pydantic models
        try:
            from pydantic import BaseModel, Field
            from typing import List as TypingList, Dict, Any, Optional
            from enum import Enum
            
            class ToolTypeEnum(str, Enum):
                DATABRICKS_SEARCH = "databricks_search"
                WEB_SEARCH = "web_search"
            
            class ToolParameters(BaseModel):
                query_text: Optional[str] = Field(None, description="Search query for databricks_search")
                query: Optional[str] = Field(None, description="Search query for web_search")
                num_results: Optional[int] = Field(5, description="Number of results for databricks_search")
            
            class ToolSelectionItem(BaseModel):
                tool_type: ToolTypeEnum = Field(description="Type of tool to use")
                confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
                reasoning: str = Field(description="Explanation of why this tool was selected")
                parameters: ToolParameters = Field(description="Tool-specific parameters")
            
            class ToolSelectionOutput(BaseModel):
                should_use_tools: bool = Field(description="Whether any tools should be used")
                selected_tools: TypingList[ToolSelectionItem] = Field(default=[], description="List of selected tools")
                reasoning: str = Field(description="Overall reasoning for tool selection decisions")
                confidence_score: float = Field(ge=0.0, le=1.0, description="Overall confidence score 0.0-1.0")
            
            response = await client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",  # Required for structured outputs
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
                temperature=0.1,
                response_format=ToolSelectionOutput
            )
            
            parsed_response = response.choices[0].message.parsed
            
            activity.logger.info(f"[STANDALONE] Agent selected {len(parsed_response.selected_tools)} tools")
            
            # Convert to our AgentToolSelectionResponse format
            return _convert_structured_response(parsed_response, available_tools)
            
        except Exception as structured_error:
            activity.logger.warning(f"[STANDALONE] Structured output failed, falling back to JSON: {structured_error}")
            
            # Fallback to regular JSON parsing
            response = await client.chat.completions.create(
                model="gpt-4o-mini",  
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            response_content = response.choices[0].message.content
            parsed_response = json.loads(response_content)
            
            activity.logger.info(f"[STANDALONE] Agent selected {len(parsed_response.get('selected_tools', []))} tools")
            
            # Convert to structured response
            return _parse_agent_response(parsed_response, available_tools)
        
    except Exception as e:
        activity.logger.error(f"[STANDALONE] Error in agent tool selection: {str(e)}")
        # Return empty selection on error
        return AgentToolSelectionResponse(
            selected_tools=[],
            reasoning=f"Tool selection failed due to error: {str(e)}",
            should_use_tools=False,
            confidence_score=0.0
        )


def _create_system_prompt() -> str:
    """Create the system prompt for the agent."""
    return """You are an intelligent tool selection agent. Your job is to analyze user queries and determine which tools (if any) should be used to provide the best response.

IMPORTANT INSTRUCTIONS:
1. Be conservative - only select tools when they would genuinely improve the response
2. Consider the user's intent carefully - don't over-interpret simple conversational messages
3. For each selected tool, provide clear reasoning and appropriate parameters
4. If no tools are needed, set should_use_tools to false

DECISION CRITERIA:
- Use databricks_search for: company/supplier/vendor lookups, business directory searches, finding service providers
- Use web_search for: current events, real-time information, recent news, market data, trending topics
- Use both tools when query requires both company data AND current information
- Use no tools for: general conversation, simple questions that don't require external data

TOOL SELECTION FIELDS:
- should_use_tools: boolean indicating whether any tools should be used
- selected_tools: array of tool selections, each containing:
  - tool_type: "databricks_search" or "web_search"
  - confidence: float between 0.0-1.0
  - reasoning: clear explanation of why this tool was selected
  - parameters: object with tool-specific parameters:
    - For databricks_search: {"query_text": "search query", "num_results": integer}
    - For web_search: {"query": "search query"}
- reasoning: overall explanation of tool selection decisions
- confidence_score: float between 0.0-1.0 for overall confidence

Be precise and only select tools that will meaningfully improve the response quality."""


def _create_user_prompt(user_query: str, conversation_context: str, tools_description: str) -> str:
    """Create the user prompt with query and available tools."""
    context_section = ""
    if conversation_context:
        context_section = f"\n\nCONVERSATION CONTEXT:\n{conversation_context}\n"
    
    return f"""USER QUERY: "{user_query}"{context_section}

AVAILABLE TOOLS:{tools_description}

Analyze the user query and determine which tools (if any) should be used. Respond with JSON only."""


def _convert_structured_response(parsed_response, available_tools: List[ToolDescriptor]) -> AgentToolSelectionResponse:
    """Convert structured output from OpenAI to AgentToolSelectionResponse."""
    try:
        # Create tool type mapping for validation
        valid_tool_types = {"databricks_search": ToolType.DATABRICKS_SEARCH, "web_search": ToolType.WEB_SEARCH}
        
        selected_tools = []
        for tool_item in parsed_response.selected_tools:
            tool_type_str = tool_item.tool_type.value if hasattr(tool_item.tool_type, 'value') else str(tool_item.tool_type)
            
            # Validate tool type
            if tool_type_str not in valid_tool_types:
                activity.logger.warning(f"Invalid tool type selected: {tool_type_str}")
                continue
            
            # Convert parameters from Pydantic model to dict
            parameters = {}
            if tool_item.parameters:
                if hasattr(tool_item.parameters, 'query_text') and tool_item.parameters.query_text:
                    parameters['query_text'] = tool_item.parameters.query_text
                if hasattr(tool_item.parameters, 'query') and tool_item.parameters.query:
                    parameters['query'] = tool_item.parameters.query
                if hasattr(tool_item.parameters, 'num_results') and tool_item.parameters.num_results:
                    parameters['num_results'] = tool_item.parameters.num_results
            
            # Create tool selection
            tool_selection = ToolSelection(
                tool_type=valid_tool_types[tool_type_str],
                confidence=tool_item.confidence,
                reasoning=tool_item.reasoning,
                parameters=parameters
            )
            selected_tools.append(tool_selection)
        
        return AgentToolSelectionResponse(
            selected_tools=selected_tools,
            reasoning=parsed_response.reasoning,
            should_use_tools=parsed_response.should_use_tools,
            confidence_score=parsed_response.confidence_score
        )
        
    except Exception as e:
        activity.logger.error(f"Error converting structured response: {str(e)}")
        return AgentToolSelectionResponse(
            selected_tools=[],
            reasoning=f"Failed to convert structured response: {str(e)}",
            should_use_tools=False,
            confidence_score=0.0
        )


def _parse_agent_response(parsed_response: Dict[str, Any], available_tools: List[ToolDescriptor]) -> AgentToolSelectionResponse:
    """Parse the agent's JSON response into structured format."""
    try:
        # Create tool type mapping for validation
        valid_tool_types = {tool.tool_type.value: tool.tool_type for tool in available_tools}
        
        selected_tools = []
        for tool_data in parsed_response.get("selected_tools", []):
            tool_type_str = tool_data.get("tool_type")
            
            # Validate tool type
            if tool_type_str not in valid_tool_types:
                activity.logger.warning(f"Invalid tool type selected: {tool_type_str}")
                continue
            
            # Create tool selection
            tool_selection = ToolSelection(
                tool_type=valid_tool_types[tool_type_str],
                confidence=max(0.0, min(1.0, float(tool_data.get("confidence", 0.0)))),
                reasoning=tool_data.get("reasoning", "No reasoning provided"),
                parameters=tool_data.get("parameters", {})
            )
            selected_tools.append(tool_selection)
        
        return AgentToolSelectionResponse(
            selected_tools=selected_tools,
            reasoning=parsed_response.get("reasoning", "No overall reasoning provided"),
            should_use_tools=bool(parsed_response.get("should_use_tools", False)),
            confidence_score=max(0.0, min(1.0, float(parsed_response.get("confidence_score", 0.0))))
        )
        
    except Exception as e:
        activity.logger.error(f"Error parsing agent response: {str(e)}")
        return AgentToolSelectionResponse(
            selected_tools=[],
            reasoning=f"Failed to parse agent response: {str(e)}",
            should_use_tools=False,
            confidence_score=0.0
        )