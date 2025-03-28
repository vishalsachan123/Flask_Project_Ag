import os
import asyncio
import logging
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.groupchat import GroupChat
from autogen_agentchat.types import TextMessage
from autogen_core.model_context import BufferedChatCompletionContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients and agents
model_client = AzureOpenAIChatCompletionClient(
    azure_deployment=os.getenv('DEPLOYMENT_NAME'),
    azure_endpoint=os.getenv('AZURE_ENDPOINT'),
    model="gpt-4o-2024-05-13",
    api_version=os.getenv('OPENAI_API_VERSION'),
    api_key=os.getenv('API_KEY'),
)

def create_agents():
    """Initialize agent team with proper async context"""
    tourism_agent = AssistantAgent(
        name="Tourism_Agent",
        system_message="You are a tourism expert...",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=5)
    )

    validator = UserProxyAgent(
        name="Validator",
        system_message="Validate responses. Reply APPROVE if correct.",
        human_input_mode="NEVER"
    )

    group_chat = GroupChat(
        agents=[tourism_agent, validator],
        messages=[],
        max_round=10
    )

    return tourism_agent, validator, group_chat

async def live_update(emit_fn, response):
    """Thread-safe updates"""
    try:
        emit_fn("update", {"message": response})
    except Exception as e:
        logger.error(f"Update failed: {str(e)}")

async def main_process(query, emit_fn):
    """Modified to handle team chat"""
    try:
        tourism_agent, validator, group_chat = create_agents()
        
        await live_update(emit_fn, "Starting conversation...")
        
        # Initiate chat
        await tourism_agent.initiate_chat(
            recipient=validator,
            message=query,
            callback=lambda msg: asyncio.create_task(
                live_update(emit_fn, str(msg))
            )
        )
        
        # Get final response
        final_response = group_chat.messages[-1].content
        await live_update(emit_fn, f"Final response: {final_response}")
        
    except Exception as e:
        logger.error(f"Process error: {str(e)}", exc_info=True)
        await live_update(emit_fn, f"Error: {str(e)}")
        # Fallback messages
        for msg in ["Processing", "Still", "Working"]:
            await asyncio.sleep(0.5)
            await live_update(emit_fn, msg)
