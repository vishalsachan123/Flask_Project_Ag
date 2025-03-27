import eventlet
eventlet.monkey_patch()  # Must be first import

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from agents import main_process
import logging
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SocketIO configuration
socketio = SocketIO(
    app,
    cors_allowed_origins=os.getenv('ALLOWED_ORIGINS', '*').split(','),
    async_mode='eventlet',
    logger=True,
    engineio_logger=True
)

@app.route('/health')
def health_check():
    return {'status': 'healthy'}, 200

@app.route("/myhome")
def index():
    return render_template("myhome.html")

@socketio.on("start_chat")
def handle_start_chat(data):
    try:
        query = data.get("query", "").strip()
        if not query:
            emit("error", {"message": "Empty query"})
            return
            
        logger.info(f"Processing query: {query[:50]}...")
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the async process
        loop.run_until_complete(main_process(query, socketio))
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        emit("error", {"message": f"Processing error: {str(e)}"})

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv('PORT', '5000')),
        debug=os.getenv('DEBUG', 'false').lower() == 'true'
    )
