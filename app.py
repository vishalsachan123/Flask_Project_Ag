from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import logging
import os
import asyncio
from dotenv import load_dotenv
from agents import main_process  # Your AutoGen main function

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SocketIO configuration with threading to avoid conflicts with AutoGen
socketio = SocketIO(
    app,
    cors_allowed_origins=os.getenv('ALLOWED_ORIGINS', '*').split(','),
    async_mode='threading',  # Avoid gevent/eventlet issues
    logger=True,
    engineio_logger=True
)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'healthy'}, 200

@app.route("/myhome")
def index():
    """Render home page"""
    return render_template("myhome.html")

@socketio.on("start_chat")
def handle_start_chat(data):
    """Handle incoming chat requests"""
    try:
        query = data.get("query", "").strip()
        if not query:
            emit("error", {"message": "Empty query"}, room=request.sid)
            return
            
        logger.info(f"Processing query: {query[:50]}...")

        # Create an emitter function that maintains socket context
        def emit_fn(event, data):
            """Emit data to the client"""
            emit(event, data, room=request.sid)

        # Run the async process without conflicting with Flask-SocketIO
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the main AutoGen process
        loop.run_until_complete(main_process(query, emit_fn))

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
