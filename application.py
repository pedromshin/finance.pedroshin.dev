import gevent.monkey
gevent.monkey.patch_all()
from decouple import config
import psycopg2
import threading
from geventwebsocket.handler import WebSocketHandler
from gevent import pywsgi
import gevent
import requests
from flask_socketio import SocketIO, emit
from flask import Flask, session
from threading import Lock


# Database configuration
db_config = {
    "dbname": config('DB_NAME'),
    "user": config('DB_USER'),
    "password": config('DB_PASSWORD'),
    "host": config('DB_HOST'),
    "port": config('DB_PORT'),
}

conn = psycopg2.connect(**db_config)

print("Database connected successfully", conn)

async_mode = None

application = Flask(__name__)
socketio = SocketIO(application, async_mode=async_mode,
                    cors_allowed_origins="*")
thread = None
thread_lock = Lock()

url = 'https://api.coinbase.com/v2/prices/btc-usd/spot'
response_event = "response_to_frontend"

streaming = True


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while streaming:
        socketio.sleep(1)
        count += 1
        price = ((requests.get(url)).json())['data']['amount']

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO btc_prices (price, timestamp) VALUES (%s, NOW())", (price,))
            conn.commit()

        print(price)
        socketio.emit(response_event,
                      {'price': price, 'count': count, 'currency': 'USD'})


@socketio.event
def my_event(message):
    receive_count = "receive_count"
    session[receive_count] = session.get(receive_count, 0) + 1
    emit(response_event,
         {'data': message['data'], 'count': session[receive_count]})


@socketio.on('control_streaming')
def control_streaming(message):
    streaming_thread = threading.Thread(target=background_thread)
    print(message)
    global streaming
    if message == 'pause':
        streaming = False
    elif message == 'stream':
        streaming = True
        if not streaming_thread.is_alive():
            # Start a new thread to resume streaming
            streaming_thread.start()


@socketio.on('connect')
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})


if __name__ == '__main__':
    server = pywsgi.WSGIServer(
        ('0.0.0.0', 5000), application, handler_class=WebSocketHandler)
    server.serve_forever()
