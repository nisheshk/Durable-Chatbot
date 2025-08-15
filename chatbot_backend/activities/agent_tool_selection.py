"""
Agent-based tool selection activity for intelligent tool recommendation.

This module provides AI-powered tool selection that replaces rigid keyword-based
intent detection with contextual, intelligent decision making.
"""

import json
from typing import List, Dict, Any
from temporalio import activity
from openai import OpenAI
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
        self.client = OpenAI(api_key=cloud_config.OPENAI_API_KEY)
    
    @activity.defn
    async def select_tools_for_query(self, request: AgentToolSelectionRequest) -> AgentToolSelectionResponse:
        """
        Use AI agent to intelligently select appropriate tools for a user query.
        
        Args:
            request: Tool selection request containing user query and available tools
            
        Returns:
            Tool selection response with selected tools and reasoning
        """
        try:
            activity.logger.info(f"Agent tool selection for query: {request.user_query}")
            
            # Format tools for agent consumption
            tools_description = format_tools_for_agent(request.available_tools)
            
            # Create the agent prompt
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(request, tools_description)
            
            # Call OpenAI to get tool selection decisions
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Use GPT-4 for better reasoning
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
    
    def _create_user_prompt(self, request: AgentToolSelectionRequest, tools_description: str) -> str:
        """Create the user prompt with query and available tools."""
        context_section = ""
        if request.conversation_context:
            context_section = f"\n\nCONVERSATION CONTEXT:\n{request.conversation_context}\n"
        
        return f"""USER QUERY: "{request.user_query}"{context_section}

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


# Create global instance for activity registration
agent_tool_selection_activity = AgentToolSelectionActivity()

# Export the activity method for use in workflows
select_tools_for_query = agent_tool_selection_activity.select_tools_for_query