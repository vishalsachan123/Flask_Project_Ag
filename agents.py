import os
from dotenv import load_dotenv
import asyncio
import logging
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.base import TaskResult
from autogen_agentchat.teams import RoundRobinGroupChat
from tools import azure_ai_search_retriever
from autogen_core.model_context import BufferedChatCompletionContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT')
API_KEY = os.getenv('API_KEY')
DEPLOYMENT_NAME = os.getenv('DEPLOYMENT_NAME')
OPENAI_API_VERSION = os.getenv('OPENAI_API_VERSION')

# Initialize Azure OpenAI client
model_client = AzureOpenAIChatCompletionClient(
    azure_deployment=DEPLOYMENT_NAME,
    azure_endpoint=AZURE_ENDPOINT,
    model="gpt-4",
    api_version=OPENAI_API_VERSION,
    api_key=API_KEY,
    timeout=30.0
)

sys_msg = """
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


# Define Agents
tourism_agent = AssistantAgent(
    name="Tourism_Agent",
    system_message=sys_msg,
    model_client=model_client,
    tools=[azure_ai_search_retriever],
    reflect_on_tool_use=True,
    model_context=BufferedChatCompletionContext(buffer_size=5),
)

user_proxy_agent = AssistantAgent(
    name="User_Proxy_Agent",
    system_message=(
        "You are a validation assistant. Review responses from the tourism_agent "
        "and validate the information before sending it to the user. If the response is correct, reply with 'APPROVE' to terminate the session. "
        "If corrections are needed, suggest improvements briefly."

    ),
    model_client=model_client,
    reflect_on_tool_use=True,
    model_context=BufferedChatCompletionContext(buffer_size=5),
)

termination = TextMentionTermination("APPROVE")
team = RoundRobinGroupChat([tourism_agent, user_proxy_agent], termination_condition=termination)

async def live_update(emit_fn, response):
    """Send live updates to client"""
    try:
        emit_fn("update", {"message": response, "ussage": 30})
    except Exception as e:
        logger.error(f"Update failed: {str(e)}")

async def main_process(query, emit_fn):
    """Main conversation processing"""
    try:
        ThoughtProcess = ''
        tourism_agent_response = ''

        async for message in team.run_stream(task=query):
            if isinstance(message, TaskResult):
                update = 'Task Completed.\n'
                ThoughtProcess += update
                await live_update(emit_fn, update)
                continue

            if isinstance(message, TextMessage):
                if message.source == 'User_Proxy_Agent':
                    update = f'Agent >> {message.source}: Suggestions: {message.content[:20]}...\n\n'
                elif message.source == 'user':
                    update = f'Agent >> {message.source}: User Query: {message.content}\n\n'
                elif message.source == 'Tourism_Agent':
                    update = f'Agent >> {message.source}: Response: {message.content}\n\n'
                    tourism_agent_response = message.content
                else:
                    update = f'Agent >> {message.source}: {message.content[:20]}...\n\n'
                
                ThoughtProcess += update
                await live_update(emit_fn, update)

            elif message.type == "ToolCallRequestEvent":
                update = f'Agent >> {message.source}: Action: ToolCallRequestEvent: ToolName: {message.content[0].name}: Arguments: {message.content[0].arguments}\n\n'
                ThoughtProcess += update
                await live_update(emit_fn, update)
           
            elif message.type == "ToolCallExecutionEvent":
                update = f'Agent >> {message.source}: Action: ToolCallExecutionEvent: ToolName: {message.content[0].name}: isError: {message.content[0].is_error}\n\n'
                ThoughtProcess += update
                await live_update(emit_fn, update)

        return {
            "ThoughtProcess": ThoughtProcess,
            "FinalResponse": tourism_agent_response,
            "token_usage": model_client._total_usage
        }

    except Exception as e:
        logger.error(f"Main process error: {str(e)}", exc_info=True)
        emit_fn("error", {"message": f"Processing error: {str(e)}"})
        raise
