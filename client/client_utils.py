from loads import *
from client.loads import *
import client.client_manager2 as client

async def request_online_users(client_sock):
    msg = client.gen_message("show_online_users", "refresh_menu_panel", "main", config["token"])
    await client.send_to_server(client_sock, msg, True)

def register_tag(tag_name):
    if tag_name in client. receieve_events:
        print(f"Tag '{tag_name}' er allerede registrert, hopper over.")
        return

    client.receieve_events[tag_name] = asyncio.Event()

