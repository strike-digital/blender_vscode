import time
import flask
import debugpy
import random
import requests
import threading
from functools import partial
from typing import Callable
from .utils import run_in_main_thread
from .environment import blender_path, scripts_folder

EDITOR_ADDRESS: str = None
OWN_SERVER_PORT: int = None
DEBUGPY_PORT: int = None


def setup(address: str, path_mappings: list[dict[str, str]]):
    global EDITOR_ADDRESS, OWN_SERVER_PORT, DEBUGPY_PORT
    EDITOR_ADDRESS = address

    OWN_SERVER_PORT = start_own_server()
    DEBUGPY_PORT = start_debug_server()

    send_connection_information(path_mappings)

    print("Waiting for debug client.")
    debugpy.wait_for_client()
    print("Debug client attached.")


def start_own_server() -> int:
    port = [None]

    def server_thread_function():
        while True:
            try:
                port[0] = get_random_port()
                server.run(debug=True, port=port[0], use_reloader=False)
            except OSError:
                pass

    thread = threading.Thread(target=server_thread_function)
    thread.daemon = True
    thread.start()

    while port[0] is None:
        time.sleep(0.01)

    return port[0]


def start_debug_server() -> int:
    while True:
        port = get_random_port()
        try:
            debugpy.listen(("localhost", port))
            break
        except OSError:
            pass
    return port


# Server
#########################################

server = flask.Flask("Blender Server")
post_handlers: dict[str, Callable] = {}


@server.route("/", methods=["POST"])
def handle_post():
    data = flask.request.get_json()
    print("Got POST:", data)

    if data["type"] in post_handlers:
        return post_handlers[data["type"]](data)

    return "OK"


@server.route("/", methods=["GET"])
def handle_get():
    flask.request
    data = flask.request.get_json()
    print("Got GET:", data)

    if data["type"] == "ping":
        pass
    return "OK"


def register_post_handler(type: str, handler: Callable[[dict], None]):
    assert type not in post_handlers
    post_handlers[type] = handler


def register_post_action(type: str, handler: Callable[[dict], None]):
    def request_handler_wrapper(data):
        run_in_main_thread(partial(handler, data))
        return "OK"

    register_post_handler(type, request_handler_wrapper)


# Sending Data
###############################


def send_connection_information(path_mappings: list[dict[str, str]]):
    send_dict_as_json(
        {
            "type": "setup",
            "blenderPort": OWN_SERVER_PORT,
            "debugpyPort": DEBUGPY_PORT,
            "blenderPath": str(blender_path),
            "scriptsFolder": str(scripts_folder),
            "addonPathMappings": path_mappings,
        }
    )


def send_dict_as_json(data: dict):
    print("Sending:", data)
    requests.post(EDITOR_ADDRESS, json=data)


# Utils
###############################


def get_random_port() -> int:
    return random.randint(2000, 10000)


def get_blender_port() -> int:
    return OWN_SERVER_PORT


def get_debugpy_port() -> int:
    return DEBUGPY_PORT


def get_editor_address() -> str:
    return EDITOR_ADDRESS
