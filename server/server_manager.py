import socket
import threading
import asyncio
import json
import subprocess
import os
import time

config_path = "server/config.json" #incase path changes
users_path = "server/users.json"

#load paths
try: #attempt fetching configs
    with open(config_path, 'r') as file:
        config = json.load(file)
        print("JSON file loaded successfully!")
except FileNotFoundError:
    print(f"Error: The file '{config_path}' does not exist.")
except json.JSONDecodeError:
    print(f"Error: The file '{config_path}' contains invalid JSON.")
except PermissionError:
    print(f"Error: Permission denied while accessing '{config_path}'.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

try: #attempt fetching users
    with open(users_path, 'r') as file:
        users = json.load(file)
        print("JSON file loaded successfully!")
except FileNotFoundError:
    print(f"Error: The file '{users_path}' does not exist.")
except json.JSONDecodeError:
    print(f"Error: The file '{users_path}' contains invalid JSON.")
except PermissionError:
    print(f"Error: Permission denied while accessing '{users_path}'.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")


HOST = config["HOST"]
PORT = config["PORT"]
client_capacity = config["user_capacity"]
func_keys = config["function_keys"]
recieve_timout = 7
timeout = 18
user_profiles = {}

async def update_users_count():
    config["user_count"] += 1

def verify_user(username):
    if username in users:
        return 1
    else:
        return 0

def ping(msg):
    config["heartbeat_time"] = time.time()
    return "pong"

def kill_server(args):
    os._exit(0)

def set_client(user):
    if user not in user_profiles:
        user_profiles[user] = {}
        user_profiles[user]["name"] = user
        user_profiles[user]["connection_error_count"] = 0
        return True
    print("WARNING! user is already online!")
    return False

async def safe_client_disconnect(client_socket, loop):
    response = {"data": ["disconnect", "heartbeat"]}
    try: 
        await loop.sock_sendall(client_socket, json.dumps(response).encode())
    except Exception as e:
        pass

    client_socket.close()
    #print("disconnect user...")
    return

async def client_recieve_handler(client_socket, loop):
    try:
        data = await asyncio.wait_for(loop.sock_recv(client_socket, 1024), recieve_timout) #format: action: ... data: ...
        data = json.loads(data.decode())
        response = None
        try:
            function = data["action"]
            msg = data["data"]
            tag = data["tag"]
         #   print(f"Successfully unpacked data \n function: {function} \n data: {msg}")
        except Exception as e:
            print(msg, function)
            print(f"Could not get function and msg: {e}")
            return
        
        if function in func_keys: 
            try:
                response = str(globals()[func_keys[function]](msg)) 
            except Exception as e:
                print(f"Function is not a valid server request: {e}")
                return False
        else:
            response = {"data": ["invalid action", tag]}
            await asyncio.wait_for(loop.sock_sendall(client_socket, json.dumps(response).encode()), recieve_timout)
            return True

        if response:
            response = {"data": [response, tag]}
            await asyncio.wait_for(loop.sock_sendall(client_socket, json.dumps(response).encode()), recieve_timout)
            return True

    except asyncio.TimeoutError:
        print("Socket timout, could not send or recieve in time")
        return False
    
    except Exception as e:
        print(f"could not recieve or send back to client {e}")
        return "Lost client"

async def client_handler(client_socket):
    loop = asyncio.get_event_loop()
    client_is_connected = True
    config["heartbeat_time"] = time.time()
    lost_conn_counter = 0
    while client_is_connected:
        crh = await client_recieve_handler(client_socket, loop)
        if crh == "Lost client":
            lost_conn_counter += 1
        else:
            lost_conn_counter = 0
        
        if lost_conn_counter == 3:
            print("Disconnected server to client")
            client_is_connected = False
            await safe_client_disconnect(client_socket, loop)

        if time.time() - config["heartbeat_time"] > timeout:
            print("Client timout! Have not recieved a ping for too long!")
            client_is_connected = False
            await safe_client_disconnect(client_socket, loop)
        
        time.sleep(0.02)

async def run_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(client_capacity)
        server_socket.setblocking(False)
        loop = asyncio.get_event_loop()
        print("Server spawned!!")
        while config["run_server"]:
            try: 
                client_socket, client_addr = await loop.sock_accept(server_socket)
                print(f"Accepted connection from {client_addr}")

                # Handle the client in a separate coroutine
                asyncio.create_task(client_handler(client_socket))

            except Exception as e:
                print("Error in main loop {e} \n")

    print("closing server\n")
    

async def main():
    await run_server()

asyncio.run(main())
