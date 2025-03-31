
import os
import time
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.base import TaskResult
from autogen_agentchat.teams import RoundRobinGroupChat
import logging

logger = logging.getLogger(__name__) 


class TourismAgentManager:
    def __init__(self,model_client,search_tool):
        self.model_client = model_client
        self.azure_ai_search_retriever = search_tool
        # System message template
        self.sys_msg = """
        You are an AI assistant for Ras Al Khaimah Tourism, dedicated to providing personalized travel recommendations 
        based on user preferences. Your role includes guiding users through an interactive trip-planning experience 
        by gathering essential details such as travel dates, group composition, and interests. 
        Utilize the 'azure_ai_search_retriever' tool to fetch accurate and up-to-date information from official sources, 
        including https://visitrasalkhaimah.com/ and https://raktda.com/, to ensure data reliability. 
        Based on the collected information, offer tailored suggestions encompassing accommodations, attractions, dining options, 
        and transportation. Present responses in a structured markdown format to enhance readability and user engagement. 
        Encourage users to refine their queries, and adapt your recommendations accordingly to craft a comprehensive and 
        personalized itinerary.
        """
        
        # Initialize agents
        self.tourism_agent = self._init_tourism_agent()
        self.user_proxy_agent = self._init_user_proxy_agent()
        self.team = self._init_team()

        logger.info("TourismAgentManager class obj initialized")

    def _init_tourism_agent(self):
        return AssistantAgent(
            name="Tourism_Agent",
            system_message=self.sys_msg,
            model_client=self.model_client,
            tools=[self.azure_ai_search_retriever],  # Import your tool
            reflect_on_tool_use=True,
            #model_context=BufferedChatCompletionContext(buffer_size=5),
        )

    def _init_user_proxy_agent(self):
        return AssistantAgent(
            name="User_Proxy_Agent",
            system_message=(
            "You are a validation assistant. Review responses from the tourism_agent "
            "and validate the information before sending it to the user. If the response is correct, reply with 'APPROVE' to terminate the session. "
            "If corrections are needed, suggest improvements briefly."
            ),
            model_client=self.model_client,
            reflect_on_tool_use=True,
            #model_context=BufferedChatCompletionContext(buffer_size=5),
        )

    def _init_team(self):
        termination = TextMentionTermination("APPROVE")
        return RoundRobinGroupChat(
            [self.tourism_agent, self.user_proxy_agent],
            termination_condition=termination,
        )

    async def process_query(self, query, conn_socketio):
        """Handle a single user query with live updates."""
        try:
            logger.info(f'processing query: {query}')
            ThoughtProcess = ""
            tourism_agent_response = ""

            async for message in self.team.run_stream(task=query):
                if isinstance(message, TaskResult):
                    c = 'Task Completed.\n'
                    ThoughtProcess += c
                    logger.info(f">> {c}")
                    await conn_socketio.emit("update", {"message": c})
                    continue

                elif isinstance(message, TextMessage):
                    if message.source == 'User_Proxy_Agent':
                        c = f'Agent >> {message.source} : Suggestions : {message.content[:20]}...\n\n'
                    elif message.source == 'user':
                        c = f'Agent >> {message.source} : User Query : {message.content}\n\n'
                    elif message.source == 'Tourism_Agent':
                        c = f'Agent >> {message.source} : Response : {message.content}...\n\n'
                        tourism_agent_response = message.content
                    else:
                        c = f'Agent >> {message.source} : {message.content[:20]}...\n\n'
                    ThoughtProcess += c
                    logger.info(f">> {c}")
                    await conn_socketio.emit("update", {"message": c})

                elif message.type == "ToolCallRequestEvent":
                    c = f'Agent >> {message.source}: Action: ToolCallRequestEvent : ToolName : {message.content[0].name} : Arguments : {message.content[0].arguments}\n\n'
                    ThoughtProcess += c
                    logger.info(f">> {c}")
                    await conn_socketio.emit("update", {"message": c})
                
                elif message.type == "ToolCallExecutionEvent":
                    c += f'Agent >> {message.source}: Action: ToolCallExecutionEvent : ToolName : {message.content[0].name} : isError : {message.content[0].is_error}\n\n'
                    ThoughtProcess += c
                    logger.info(f">> {c}")
                    await conn_socketio.emit("update", {"message": c})


                else:
                    await conn_socketio.emit("update", {"message": "some other type"})

            response = {
                "ThoughtProcess" : ThoughtProcess,
                "Finalresponse" : tourism_agent_response,
                "total_prompt_tokens" : self.model_client._total_usage.prompt_tokens,
                "total_completion_tokens" : self.model_client._total_usage.completion_tokens
            }
            logger.info(f">> prompt tokens:  {self.model_client._total_usage.prompt_tokens}")
            logger.info(f">>completion {self.model_client._total_usage.completion_tokens}")

        except Exception as e:
            logger.error(f"Main process error: {str(e)}", exc_info=True)
            await conn_socketio.emit("update", {"message":  f"Processing error: {str(e)}"})
            bucket = ["call", "nhi", "lag", "rhi","call", "nhi", "lag", "rhi"]
            for i in bucket:
                time.sleep(0.5)
                await conn_socketio.emit("update", {"message":  i})
            
        

