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
    engineio_logger=True,
    ping_timeout=60,  # Wait 60 seconds for a pong
    ping_interval=25  # Send ping every 25 seconds
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
    """Handle incoming chat requests asynchronously."""
    try:
        query = data.get("query", "").strip()
        if not query:
            socketio.emit("error", {"message": "Empty query"}, room=request.sid)
            return

        logger.info(f"Processing query: {query[:50]}...")

        # Use start_background_task to run async task safely
        socketio.start_background_task(run_async_chat, query, request.sid)

    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        socketio.emit("error", {"message": f"Processing error: {str(e)}"}, room=request.sid)


# Define async task separately
def run_async_chat(query, sid):
    """Run the AutoGen process in a background task."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def process_chat():
            def emit_fn(event, data):
                """Emit data to the client"""
                socketio.emit(event, data, room=sid)

            # Run the main AutoGen process asynchronously
            await main_process(query, emit_fn)

        loop.run_until_complete(process_chat())
    except Exception as e:
        logger.error(f"Background task error: {str(e)}", exc_info=True)
        socketio.emit("error", {"message": f"Background task error: {str(e)}"}, room=sid)

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv('PORT', '5000')),
        debug=False
    )
