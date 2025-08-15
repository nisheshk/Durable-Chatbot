import asyncio
from collections import deque
from datetime import timedelta
from typing import Deque, List, Optional, Tuple

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.openai_activities import (
        OpenAIActivities, 
        databricks_search_company_info, 
        web_search_realtime_info
    )
    from activities.agent_tool_selection import select_tools_for_query
    from shared.models import (
        DatabricksSearchRequest, 
        WebSearchRequest,
        AgentToolSelectionRequest,
        ToolType
    )
    from shared.tool_descriptors import get_all_tool_descriptors


@workflow.defn
class SignalQueryOpenAIWorkflow:
    def __init__(self) -> None:
        # List to store prompt history
        self.conversation_history: List[Tuple[str, str]] = []
        self.prompt_queue: Deque[str] = deque()
        self.conversation_summary = ""
        self.chat_timeout: bool = False
        self.session_complete: bool = False
        self.user_id: Optional[int] = None

    @workflow.run
    async def run(self, inactivity_timeout_minutes: int, user_id: int = None) -> str:
        self.user_id = user_id
        while True:
            workflow.logger.info(
                "Waiting for prompts... or closing chat after "
                + f"{inactivity_timeout_minutes} minute(s)"
            )

            # Wait for a chat message (signal), completion signal, or timeout
            try:
                await workflow.wait_condition(
                    lambda: bool(self.prompt_queue) or self.session_complete,
                    timeout=timedelta(minutes=inactivity_timeout_minutes),
                )
            # If timeout was reached
            except asyncio.TimeoutError:
                self.chat_timeout = True
                workflow.logger.info("Chat closed due to inactivity")
                # End the workflow
                break
            
            # Check if session completion was requested
            if self.session_complete:
                workflow.logger.info("Session completion requested - ending workflow")
                break

            while self.prompt_queue:
                # Fetch next user prompt and add to conversation history
                prompt = self.prompt_queue.popleft()
                self.conversation_history.append(("user", prompt))

                workflow.logger.info(f"Prompt: {prompt}")

                # Process with tools to get additional context
                tool_context = await self.process_with_tools(prompt)
                
                # Enhance prompt with tool results if available
                if tool_context:
                    enhanced_prompt = f"User query: {prompt}\n\nAdditional context from tools:\n{tool_context}\n\nPlease provide a comprehensive response using both the conversation history and the additional context."
                else:
                    enhanced_prompt = prompt

                # Send the enhanced prompt to OpenAI
                response = await workflow.execute_activity_method(
                    OpenAIActivities.prompt_openai,
                    self.prompt_with_history(enhanced_prompt),
                    schedule_to_close_timeout=timedelta(minutes=2),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=1),
                        maximum_interval=timedelta(seconds=30),
                        maximum_attempts=3,
                        backoff_coefficient=2.0
                    )
                )

                workflow.logger.info(f"{response}")

                # Append the response to the conversation history
                self.conversation_history.append(("response", response))
                
                # Save conversation to database after each response (for immediate access)
                if self.user_id:
                    await workflow.execute_activity(
                        OpenAIActivities.save_conversation_to_db,
                        args=[self.user_id, self.conversation_history, None],  # No summary yet
                        schedule_to_close_timeout=timedelta(seconds=30),
                        retry_policy=RetryPolicy(
                            initial_interval=timedelta(seconds=1),
                            maximum_interval=timedelta(seconds=10),
                            maximum_attempts=2,
                            backoff_coefficient=2.0
                        )
                    )

        # Generate a summary before ending the workflow
        self.conversation_summary = await workflow.execute_activity(
            OpenAIActivities.prompt_openai,
            args=[self.prompt_summary_from_history()],
            schedule_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=30),
                maximum_attempts=3,
                backoff_coefficient=2.0
            )
        )

        workflow.logger.info(f"Conversation summary:\n{self.conversation_summary}")

        # Save conversation to database before ending
        if self.user_id:
            await workflow.execute_activity(
                OpenAIActivities.save_conversation_to_db,
                args=[self.user_id, self.conversation_history, self.conversation_summary],
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    maximum_attempts=2,
                    backoff_coefficient=2.0
                )
            )

        return f"{self.conversation_history}"

    @workflow.signal
    async def user_prompt(self, prompt: str) -> None:
        # Chat timed out but the workflow is waiting for a chat summary to be generated
        if self.chat_timeout:
            workflow.logger.warn(f"Message dropped due to chat closed: {prompt}")
            return

        self.prompt_queue.append(prompt)

    @workflow.signal
    async def complete_session(self) -> None:
        """Signal to complete the session after all messages are processed."""
        workflow.logger.info("Session completion signal received")
        self.session_complete = True

    @workflow.query
    def get_conversation_history(self) -> List[Tuple[str, str]]:
        return self.conversation_history

    @workflow.query
    def get_summary_from_history(self) -> str:
        return self.conversation_summary

    # Helper method used in prompts to OpenAI
    def format_history(self) -> str:
        return " ".join(f"{text}" for _, text in self.conversation_history)
    
    # Get last n messages from conversation history
    def get_last_n_messages(self, n: int) -> List[Tuple[str, str]]:
        if n <= 0:
            return []
        return self.conversation_history[-n:]
    
    # Get last n tokens from conversation history (approximate token count)
    def get_last_n_tokens(self, n: int) -> List[Tuple[str, str]]:
        if n <= 0:
            return []
        
        # Simple token approximation: 1 token ≈ 4 characters
        token_count = 0
        result = []
        
        # Iterate backwards through conversation history
        for speaker, text in reversed(self.conversation_history):
            # Approximate token count for this message
            message_tokens = len(text) // 4
            
            # If adding this message would exceed n tokens, stop
            if token_count + message_tokens > n:
                break
                
            result.insert(0, (speaker, text))
            token_count += message_tokens
            
        return result

    # Create the prompt given to OpenAI for each conversational turn
    def prompt_with_history(self, prompt: str) -> str:
        #This is the full history
        #history_string = self.format_history()
        
        # Get last 50 tokens of conversation history
        limited_history = self.get_last_n_tokens(1000)
        history_string = " ".join(f"{text}" for _, text in limited_history)
        return (
            f"Here is the conversation history: {history_string} Please add "
            + "a few sentence response to the prompt in plain text sentences. "
            + "Don't editorialize or add metadata like response. Keep the "
            + f"text a plain explanation based on the history. Prompt: {prompt}"
        )

    # Create the prompt to OpenAI to summarize the conversation history
    def prompt_summary_from_history(self) -> str:
        history_string = self.format_history()
        return (
            "Here is the conversation history between a user and a chatbot: "
            + f"{history_string}  -- Please produce a two sentence summary of "
            + "this conversation."
        )
    
    
    async def process_with_tools(self, prompt: str) -> str:
        """Process prompt using agent-based tool selection for enhanced context."""
        
        try:
            # Prepare conversation context (last few messages for agent context)
            context_messages = self.get_last_n_messages(3)
            conversation_context = " ".join([f"{speaker}: {text}" for speaker, text in context_messages])
            
            # Get all available tool descriptors
            available_tools = get_all_tool_descriptors()
            
            # Create agent tool selection request
            selection_request = AgentToolSelectionRequest(
                user_query=prompt,
                conversation_context=conversation_context if conversation_context.strip() else None,
                available_tools=available_tools
            )
            
            # Let the agent decide which tools to use
            workflow.logger.info("Requesting agent-based tool selection")
            tool_selection = await workflow.execute_activity(
                select_tools_for_query,
                selection_request,
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    maximum_attempts=2,
                    backoff_coefficient=2.0
                )
            )
            
            # Handle both dict and object types from Temporal
            if isinstance(tool_selection, dict):
                should_use_tools = tool_selection.get('should_use_tools', False)
                selected_tools = tool_selection.get('selected_tools', [])
                confidence_score = tool_selection.get('confidence_score', 0.0)
                reasoning = tool_selection.get('reasoning', '')
            else:
                should_use_tools = tool_selection.should_use_tools
                selected_tools = tool_selection.selected_tools
                confidence_score = tool_selection.confidence_score
                reasoning = tool_selection.reasoning
            
            workflow.logger.info(f"Agent tool selection: should_use_tools={should_use_tools}, "
                               f"selected {len(selected_tools)} tools, "
                               f"confidence={confidence_score}")
            
            # If no tools should be used, return empty context
            if not should_use_tools or not selected_tools:
                workflow.logger.info("Agent determined no tools needed")
                return ""
            
            # Execute selected tools
            tool_results = []
            for tool in selected_tools:
                try:
                    # Handle both dict and object types for tools
                    if isinstance(tool, dict):
                        tool_type = tool.get('tool_type')
                    else:
                        tool_type = tool.tool_type
                    
                    if tool_type == ToolType.DATABRICKS_SEARCH or tool_type == 'databricks_search':
                        result = await self._execute_databricks_search(tool, prompt)
                        if result:
                            tool_results.append(result)
                    
                    elif tool_type == ToolType.WEB_SEARCH or tool_type == 'web_search':
                        result = await self._execute_web_search(tool, prompt)
                        if result:
                            tool_results.append(result)
                    
                except Exception as e:
                    tool_type_str = tool_type if isinstance(tool_type, str) else tool_type.value if hasattr(tool_type, 'value') else str(tool_type)
                    workflow.logger.error(f"Error executing {tool_type_str}: {str(e)}")
                    tool_results.append(f"{tool_type_str} search encountered an error, proceeding with general response.")
            
            # Return combined tool results
            if tool_results:
                return f"Tool Selection Reasoning: {reasoning}\n\n" + "\n\n".join(tool_results)
            else:
                return ""
                
        except Exception as e:
            workflow.logger.error(f"Error in agent-based tool selection: {str(e)}")
            return ""
    
    async def _execute_databricks_search(self, tool_selection, original_prompt: str) -> str:
        """Execute Databricks search based on agent selection."""
        workflow.logger.info("Executing agent-selected Databricks search")
        
        # Extract parameters from agent selection (handle both dict and object)
        if isinstance(tool_selection, dict):
            params = tool_selection.get("parameters", {})
        else:
            params = tool_selection.parameters
        
        query_text = params.get("query_text", original_prompt)
        num_results = params.get("num_results", 5)
        
        # Create Databricks search request
        databricks_request = DatabricksSearchRequest(
            endpoint_name="procurement_calendar",
            index_name="procurement_calendar.silver.companies_vs_index", 
            query_text=query_text,
            num_results=min(max(1, num_results), 10),  # Clamp between 1-10
            columns=["company_name", "city", "state", "phone", "website", "email", "capability", "scope_of_work_ranges"]
        )
        
        # Execute the search
        company_result = await workflow.execute_activity(
            databricks_search_company_info,
            databricks_request,
            schedule_to_close_timeout=timedelta(seconds=90),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=2),
                maximum_interval=timedelta(seconds=60),
                maximum_attempts=3,
                backoff_coefficient=2.0
            )
        )
        
        if company_result.total_results > 0:
            result_lines = [f"Company Search Results: {company_result.total_results} companies found matching your query."]
            
            # Format top 3 company results
            for i, row in enumerate(company_result.data_array[:3]):
                company_data = dict(zip(company_result.columns, row))
                company_info = f"Company {i+1}: {company_data.get('company_name', 'N/A')}"
                
                if company_data.get('phone'):
                    company_info += f", Phone: {company_data['phone']}"
                if company_data.get('email'):
                    company_info += f", Email: {company_data['email']}" 
                if company_data.get('city') and company_data.get('state'):
                    company_info += f", Location: {company_data['city']}, {company_data['state']}"
                if company_data.get('capability'):
                    capability = str(company_data['capability'])[:100]
                    company_info += f", Capabilities: {capability}{'...' if len(str(company_data['capability'])) > 100 else ''}"
                    
                result_lines.append(company_info)
            
            return "\n".join(result_lines)
        
        return "No companies found matching the search criteria."
    
    async def _execute_web_search(self, tool_selection, original_prompt: str) -> str:
        """Execute web search based on agent selection."""
        workflow.logger.info("Executing agent-selected web search")
        
        # Extract query from agent selection or use original prompt (handle both dict and object)
        if isinstance(tool_selection, dict):
            params = tool_selection.get("parameters", {})
        else:
            params = tool_selection.parameters
            
        query = params.get("query", original_prompt)
        
        # Create web search request
        web_request = WebSearchRequest(
            query=query,
            max_results=5  # Default value, OpenAI handles the actual search scope
        )
        
        # Execute the search
        web_result = await workflow.execute_activity(
            web_search_realtime_info,
            web_request,
            schedule_to_close_timeout=timedelta(seconds=90),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=2),
                maximum_interval=timedelta(seconds=60),
                maximum_attempts=3,
                backoff_coefficient=2.0
            )
        )
        
        return f"Current Web Information: {web_result.summary}"
