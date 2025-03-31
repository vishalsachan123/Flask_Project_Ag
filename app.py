from gevent import monkey
monkey.patch_all()

import asyncio
from flask import Flask, render_template
from flask_socketio import SocketIO
from agent_ki_class import TourismAgentManager
from tool_ki_class import AzureAISearchTool
import logging
import os
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize SocketIO with proper async handling
socketio = SocketIO(
    app,
    cors_allowed_origins=os.getenv('ALLOWED_ORIGINS', '*').split(','),
    async_mode='gevent',
    logger=True,
    engineio_logger=True
)

# Azure Search Configuration
service_endpoint = os.getenv('service_endpoint')
key = os.getenv('key')
indexname = os.getenv('indexname')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'healthy'}, 200


@app.route("/myhome")
def index():
    return render_template("myhome.html")

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

@socketio.on("start_chat")
def handle_start_chat(data):
    
    query = data.get("query", "").strip()
    
    if not query:
        logger.info("Empty query received")
        socketio.emit("error", {"message": "Query cannot be empty"})
        return
    
    logger.info(f"Processing query: {query[:50]}...")
    
    try:
        model_client = AzureOpenAIChatCompletionClient(
            azure_deployment=os.getenv('DEPLOYMENT_NAME'),
            azure_endpoint=os.getenv('AZURE_ENDPOINT'),
            model="gpt-4o-2024-05-13",
            api_version=os.getenv('OPENAI_API_VERSION'),
            api_key=os.getenv('API_KEY'),
        )

        # Initialize Azure Search client
        search_client = SearchClient(
            service_endpoint, 
            indexname, 
            AzureKeyCredential(key)
        )
        
        search_tool_obj = AzureAISearchTool(search_client=search_client)
        
        # Initialize and use agent manager
        agent_manager = TourismAgentManager(
            model_client=model_client,
            search_tool=search_tool_obj.azure_ai_search_retriever
        )

        loop.run_until_complete(agent_manager.process_query(query, socketio))

        
    except Exception as e:
        logger.error(f"Chat initialization error: {str(e)}", exc_info=True)
        socketio.emit("error", {"message": f"Failed to start chat: {str(e)}"})



if __name__ == "__main__":
    socketio.run(
        app, 
        host="0.0.0.0", 
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
    )