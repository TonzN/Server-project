from loads import *
from client.loads import *
import client.client_manager2 as client

def request_online_users():
    msg = client.gen_message("show_online_users", "refresh_menu_panel", "main", config["token"])
    client.send_to_server(config["client_sock"], msg)