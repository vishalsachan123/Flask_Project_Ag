import os
from dotenv import load_dotenv
import json
import asyncio
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.base import TaskResult
from autogen_agentchat.teams import RoundRobinGroupChat
from tools import azure_ai_search_retriever
from autogen_core.model_context import BufferedChatCompletionContext
import time
import logging

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
    model="gpt-4o-2024-05-13",
    api_version=OPENAI_API_VERSION,
    api_key=API_KEY,
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
    reflect_on_tool_use=True,
    model_context=BufferedChatCompletionContext(buffer_size=5),
)

# Define Validation Agent with Auto-Approval
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

team = RoundRobinGroupChat([tourism_agent,user_proxy_agent], termination_condition=termination)


async def live_update(emit_fn, response):
    """Send live updates to client"""
    try:
        emit_fn("update", {"message": response, "usage": 30})  # Corrected typo from 'ussage' to 'usage'
    except Exception as e:
        logger.error(f"Live update failed: {str(e)}")


async def main_process(query, emit_fn):
    """Main conversation processing"""
    try:
        ThoughtProcess = ''
        tourism_agent_response = ''
    
        async for message in team.run_stream(task=query):
            if isinstance(message, TaskResult):
                c = 'Task Completed.\n'
                ThoughtProcess += c
                print(c)
                await live_update(emit_fn,c)
                continue
    
            if isinstance(message, TextMessage):
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
                print(c)
                await live_update(emit_fn,c)
    
            elif message.type == "ToolCallRequestEvent":
                c = f'Agent >> {message.source}: Action: ToolCallRequestEvent : ToolName : {message.content[0].name} : Arguments : {message.content[0].arguments}\n\n'
                ThoughtProcess += c
                print(c)
                await live_update(emit_fn,c)
               
            elif message.type == "ToolCallExecutionEvent":
                c += f'Agent >> {message.source}: Action: ToolCallExecutionEvent : ToolName : {message.content[0].name} : isError : {message.content[0].is_error}\n\n'
                ThoughtProcess += c
                print(c)
                await live_update(emit_fn,c)
    
    
            else:
                pass
    
        response = {
            "ThoughtProcess" : ThoughtProcess,
            "Finalresponse" : tourism_agent_response,
            "total_prompt_tokens" : model_client._total_usage.prompt_tokens,
            "total_completion_tokens" : model_client._total_usage.completion_tokens
        }
        
    

    
    except Exception as e:
        logger.error(f"Main process error: {str(e)}", exc_info=True)
        #emit_fn("error", {"message": f"Processing error: {str(e)}"})
        await live_update(emit_fn, f"Processing error: {str(e)}")
        bucket = ["call", "nhi", "lag", "rhi","call", "nhi", "lag", "rhi"]
        for i in bucket:
            time.sleep(0.5)
            await live_update(emit_fn, i)
