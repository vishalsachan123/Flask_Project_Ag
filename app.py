# from flask import Flask, request, jsonify
# import asyncio
# from app.agents import main_process

# # Flask App
# app = Flask(__name__)

# # Create a global event loop
# loop = asyncio.new_event_loop()
# asyncio.set_event_loop(loop)

# @app.route("/chat", methods=["GET"])
# def chat():
#     """Handle chat requests and return results."""
#     query = request.args.get('query')
#     result = loop.run_until_complete(main_process(query))
#     return jsonify({"response": result})

# if __name__ == "__main__":
#     app.run(debug=True)

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from agents import main_process

import asyncio

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


# WebSocket handler when chat starts
@socketio.on("start_chat")
def start_chat(data):
    query = data["query"]
    loop.run_until_complete(main_process(query,socketio))

# Serve the HTML frontend
@app.route("/myhome")
def index():
    return render_template("myhome.html")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
