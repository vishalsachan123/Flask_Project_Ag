from gevent import monkey
monkey.patch_all(thread=False, select=False)  # Crucial for asyncio compatibility

from flask import Flask, request
from flask_socketio import SocketIO, emit
import logging
import os
import asyncio
from threading import Lock
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
socketio = SocketIO(
    app,
    async_mode='gevent',
    cors_allowed_origins=os.getenv('ALLOWED_ORIGINS', '*').split(','),
    logger=True,
    engineio_logger=True
)

# Thread-safe task management
task_lock = Lock()
active_tasks = {}

@socketio.on("start_chat")
def handle_start_chat(data):
    def emit_fn(event, data):
        emit(event, data, room=request.sid)
    
    query = data.get("query", "").strip()
    if not query:
        emit_fn("error", {"message": "Empty query"})
        return

    logger.info(f"Processing: {query[:50]}...")
    
    # Create isolated event loop
    loop = asyncio.new_event_loop()
    
    try:
        from agents import main_process
        task = loop.create_task(main_process(query, emit_fn))
        
        with task_lock:
            active_tasks[request.sid] = (loop, task)
        
        loop.run_until_complete(task)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        emit_fn("error", {"message": str(e)})
    finally:
        with task_lock:
            if request.sid in active_tasks:
                loop.close()
                del active_tasks[request.sid]

@socketio.on("disconnect")
def handle_disconnect():
    with task_lock:
        if request.sid in active_tasks:
            loop, task = active_tasks.pop(request.sid)
            task.cancel()
            loop.stop()
            loop.close()
