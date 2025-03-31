from flask import Flask, render_template
from flask_socketio import SocketIO
from agent_ki_class import TourismAgentManager  # Updated import
from tool_ki_class import AzureAISearchTool
import logging
import os
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv



app = Flask(__name__)

socketio = SocketIO(
    app,
    cors_allowed_origins=os.getenv('ALLOWED_ORIGINS', '*').split(','),
    async_mode='gevent',
    logger=True,
    engineio_logger=True
)

# Initialize manager (stateless, creates agents per request)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()



@socketio.on("start_chat")
def handle_start_chat(data):
    query = data["query"]
    
    try:
        if not query:
            logger.info(f"Empty query.")
            return
        logger.info(f"Processing query: {query[:50]}...")

        # Run in background to avoid blocking
        socketio.start_background_task(
        async_process_query, 
        query=query,
        conn_socketio=socketio
        )
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)


async def async_process_query(query, conn_socketio):
    try:

        model_client = AzureOpenAIChatCompletionClient(
        azure_deployment=os.getenv('DEPLOYMENT_NAME'),
        azure_endpoint=os.getenv('AZURE_ENDPOINT'),
        model="gpt-4o-2024-05-13",
        api_version=os.getenv('OPENAI_API_VERSION'),
        api_key=os.getenv('API_KEY'),
        )

        service_endpoint = os.getenv('service_endpoint')
        key = os.getenv('key')
        indexname = os.getenv('indexname')

        search_client = SearchClient(service_endpoint, indexname, AzureKeyCredential(key))

        search_tool_obj  = AzureAISearchTool(search_client=search_client)
        agent_manager = TourismAgentManager(model_client=model_client,search_tool= search_tool_obj.azure_ai_search_retriever)
        await agent_manager.process_query(query, conn_socketio)
    
    except Exception as e:
        logger.error(f"error: {str(e)}", exc_info=True)

@app.route("/myhome")
def index():
    return render_template("myhome.html")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))