import eventlet
eventlet.monkey_patch()  # Must be first import

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
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

async def chatbot_simulation(query, emit_fn):
    """Simulate chatbot processing with proper socket emission"""
    responses = [
        f"Processing your query: {query}...",
        "Searching for relevant information...",
        "Analyzing data...",
        "Finalizing the response...",
        "Here's the result: The information you requested!"
    ]
    
    for response in responses:
        try:
            await asyncio.sleep(2)  # Simulate processing time
            # Use the provided emit function
            emit_fn("update", {"message": response})
        except Exception as e:
            logger.error(f"Error in simulation: {str(e)}")
            emit_fn("error", {"message": "Processing update failed"})
            break

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
            emit("error", {"message": "Empty query"}, room=request.sid)
            return
            
        logger.info(f"Processing query: {query[:50]}...")
        
        # Create an emitter function that maintains socket context
        def emit_fn(event, data):
            emit(event, data, room=request.sid)
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the async process with the emitter function
        loop.run_until_complete(chatbot_simulation(query, emit_fn))
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        emit("error", {"message": f"Processing error: {str(e)}"}, room=request.sid)

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv('PORT', '5000')),
        debug=os.getenv('DEBUG', 'false').lower() == 'true'
    )
