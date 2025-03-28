import os
from dotenv import load_dotenv
import asyncio
import logging
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core import CancellationToken

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


sys_msg = "You are a tourism agent that will answer user queries."

# Define Agents
tourism_agent = AssistantAgent(
    name="Tourism_Agent",
    system_message=sys_msg,
    model_client=model_client,
    reflect_on_tool_use=True,
    model_context=BufferedChatCompletionContext(buffer_size=5),
)


async def live_update(emit_fn, response):
    """Send live updates to client"""
    try:
        emit_fn("update", {"message": response, "usage": 30})  # Corrected typo from 'ussage' to 'usage'
    except Exception as e:
        logger.error(f"Live update failed: {str(e)}")


async def main_process(query, emit_fn):
    """Main conversation processing"""
    try:
        # Get response from the agent
        response = await tourism_agent.on_messages(
            [TextMessage(content=query, source="user")],
            cancellation_token=CancellationToken(),
        )
        
        # Print or log for debugging
        logger.info(f"Agent Response: {response.inner_messages}")
        
        # Send response to client
        if response and response.chat_message:
            await live_update(emit_fn, str(response.chat_message.content))
        else:
            await live_update(emit_fn, "No response generated.")
    
    except Exception as e:
        logger.error(f"Main process error: {str(e)}", exc_info=True)
        #emit_fn("error", {"message": f"Processing error: {str(e)}"})
        live_update(emit_fn, f"Processing error: {str(e)}")
