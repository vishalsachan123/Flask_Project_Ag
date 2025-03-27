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
dotenv_path="D:/RND/tourism_agent_flask/.env"
# Load environment variables
load_dotenv()
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT')
API_KEY = os.getenv('API_KEY')
DEPLOYMENT_NAME = os.getenv('DEPLOYMENT_NAME')
OPENAI_API_VERSION = os.getenv('OPENAI_API_VERSION')


async def chatbot_simulation(query,conn_socketio):
    responses = [
        f"Processing your query: {query}...",
        "Searching for relevant information...",
        "Analyzing data...",
        "Finalizing the response...",
        "Here’s the result: The information you requested!"
    ]
   
    for response in responses:
        await asyncio.sleep(2)  # Simulate delay of 2 seconds
        conn_socketio.emit("update", {"message": response})



async def live_update(conn_socketio,response):
    conn_socketio.emit("update", {"message": response,"ussage":30})

async def main_process(query,conn_socketio):
    """Start conversation and return structured JSON results."""
    await chatbot_simulation(query,conn_socketio)

   
    
    
