from threading import Lock
from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit
import requests

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

application = Flask(__name__)
socketio = SocketIO(application, async_mode=async_mode,
                    cors_allowed_origins="*")
thread = None
thread_lock = Lock()

url = 'https://api.coinbase.com/v2/prices/btc-usd/spot'
response_event = "response_to_frontend"


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        print(count)
        socketio.sleep(3)
        count += 1
        price = ((requests.get(url)).json())['data']['amount']
        socketio.emit(response_event,
                      {'price': price, 'count': count, 'currency': 'USD'})


@socketio.event
def my_event(message):
    receive_count = "receive_count"
    session[receive_count] = session.get(receive_count, 0) + 1
    emit(response_event,
         {'data': message['data'], 'count': session[receive_count]})


@socketio.on('message_from_frontend')
def handle_message_from_frontend(message):
    emit(response_event, {'data': 'Server received: ' + message})


@socketio.on('connect')
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})


if __name__ == '__main__':
    socketio.run(application, host='0.0.0.0', port=5000, debug=True)
