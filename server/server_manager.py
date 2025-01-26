import socket
import threading
import asyncio
import json
import subprocess
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
recieve_timout = 5

async def update_users_count():
    config["user_count"] += 1

def verify_user(username):
    if username in users:
        return 1
    else:
        return 0

def ping(msg):
    if msg == "ping":
        return "pong"

async def safe_client_disconnect(client_socket, loop):
    response = "disconnect"
    try: 
        await loop.sock_sendall(client_socket, json.dumps(response).encode())
    except asyncio.TimeoutError:
        pass

    client_socket.close()
    #print("disconnect user...")
    return

async def client_recieve_handler(client_socket, loop):
    try:
        data = await asyncio.wait_for(loop.sock_recv(client_socket, 1024), recieve_timout) #format: action: ... data: ...
        data = json.loads(data.decode())
 
        try:
            function = data["action"]
            msg = data["data"]
            #print(f"Successfully unpacked data \n function: {function} \n data: {msg}")
        except Exception as e:
            print(msg, function)
            print(f"Could not get function and msg: {e}")
            return
       
        if function in func_keys: 
            try:
                response = str(globals()[func_keys[function]](msg)) 
            except Exception as e:
                response = None
                print(f"Function is not a valid server request: {e}")
                return False

        if response:
            response = {"data": [response]}
            await asyncio.wait_for(loop.sock_sendall(client_socket, json.dumps(response).encode()), recieve_timout)
            return True
    
    except asyncio.TimeoutError:
        print("Socket timout, could not send or recieve in time")
        return False
    
    except Exception as e:
        print(f"could not recieve or send back to client {e}")
        return False

async def client_handler(client_socket):
    loop = asyncio.get_event_loop()
    client_is_connected = True
    while client_is_connected:
        await client_recieve_handler(client_socket, loop)
        client_is_connected = False
        await safe_client_disconnect(client_socket, loop)

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
