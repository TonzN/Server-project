import socket
import threading
import asyncio
import json
import uuid
import time
import os
import jwt
import datetime
import server_utils as utils

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
recieve_timeout = 5
standby_time = 60*3
timeout = 15
user_profiles = {}
#all functrions created must have an id passed

def change_persmission_level(data, token):
    try: #checks if data is given in the right way
        target_user = data[0]
        new_access_level = data[1]
    except:
        return "Invalid data"
    if not target_user in users:
        return "Target user does not exist"

    profile = get_user_profile(token) #gets session profile from token
    if profile: 
        username = profile["name"]
        if username in users: #double checks if user has a server profile
            access_level = users[username]["permission_level"] 
            if not "change_to_"+new_access_level in config["access_level"]:
                return "access_level does not exist"
            if access_level in config["access_level"]["change_to_"+new_access_level]:
                users[target_user]["permission_level"] = new_access_level
                return "Success"
            else:
                return "Not high enough access level to do this"
        else:
            return "Userprofile is missing"
    else:
        return "Invalid token"

def kill_server(msg, token):
    user = get_user_profile(token)
    if user["id"]:
        if users[user["name"]]["permission_level"] == "admin":
            print(f"User {user["name"]}|{user["id"]} killed the server!!")
            print(msg)
            os._exit(0)
        else:
            return "Not high enough access level"
    return "Unverfied token"

def update_users_count(amount = 1):
    config["user_count"] += amount
    with open(config_path, "w") as file:
        json.dump(config, file, indent=4)  # Pretty print with indentation

def verify_user(user_data):
    try:
        username = user_data["username"]
        password = user_data["password"]
    except Exception as e:
        print("invalid data provided")
        return 0
    if username in users:
        if utils.verify_password(users[username]["password"], password):
            return 1
    return 0

def get_user_profile(token):
    payload = utils.validate_token(token)
    if payload:
        session_key = payload["session_key"]
        if session_key in user_profiles:
            return user_profiles[session_key]
        else:
            print("INVALID session key")
            return False
    else:
        print(f"INVALID TOKEN {token}")
        return False
    
def ping(msg, token):
    user = get_user_profile(token)
    if user:
        if msg == "ping":
            print("ping")
        user["heartbeat"] = time.time()
        return "pong"
    return False

def set_client(userdata)    : #only used when a client joins! profile contains server data important to run clients
    try: 
        user = userdata["user"]
        sock = userdata["socket"]
    except Exception as e:
        print(f"invalid userdata {user} {sock} {e}")
        return False
    
    if not user in user_profiles:
        id = utils.gen_user_id()
        token = utils.generate_token(id)
        payload = utils.validate_token(token)
        if payload: 
            session_key = payload["session_key"]
            user_profiles[session_key] = {}
            user_profiles[session_key]["name"] = user
            user_profiles[session_key]["id"] = payload["user_id"]
            user_profiles[session_key]["connection_error_count"] = 0
            user_profiles[session_key]["heartbeat"] = time.time()
            user_profiles[session_key]["socket"] = sock
            print(f"User: {user} connected to server")
            return token 
        print("Weird things happens with token")
    return False

async def safe_client_disconnect(client_socket, loop):
    response = "disconnect"
    try: 
        await loop.sock_sendall(client_socket, json.dumps(response).encode())
    except Exception as e:
        pass

    client_socket.close()
    #print("disconnect user...")
    return

async def client_recieve_handler(client_socket, loop, recieve_timout):
    try:
        data = await asyncio.wait_for(loop.sock_recv(client_socket, 1024), recieve_timout) #format: action: ... data: ...
        data = json.loads(data.decode())
        response = None
        try:
            function = data["action"]
            msg = data["data"]
            tag = data["tag"]
            token = data["token"]
         #   print(f"Successfully unpacked data \n function: {function} \n data: {msg}")
        except Exception as e:
            print(msg, function, tag)
            print(f"Could not get function and msg: {e}")
            return
        
        if function in func_keys: 
            try:
                if token: #function requires authentication
                    response = str(globals()[func_keys[function]](msg, token)) 
                else:
                    response = str(globals()[func_keys[function]](msg)) 
            except Exception as e:
                print(f"Function is not a valid server request: {e}\n Error at: {function}")
                response = json.dumps({"data": ["Attempted running function and failed", tag]}) + "\n"
                await asyncio.wait_for(loop.sock_sendall(client_socket, response.encode()), recieve_timout)
                return False
        else:
            response = json.dumps({"data": ["invalid action", tag]}) + "\n"
            await asyncio.wait_for(loop.sock_sendall(client_socket, response.encode()), recieve_timout)
            return False

        if response:
            msg = response
            response = json.dumps({"data": [response, tag]}) + "\n"
            await asyncio.wait_for(loop.sock_sendall(client_socket, response.encode()), recieve_timout)
            if function == "veus":
                return [function, msg]
            if function == "set_user":
                return [function, msg]
            if function == "create_user":
                return [function, msg]
            
            return function

    except asyncio.TimeoutError:
        print("Socket timout, could not send or recieve in time")
        return "Lost client"
    
    except Exception as e:
        print(f"could not recieve or send back to client {e}")
        return "Lost client"

async def login(client_socket, loop):
    """Manages login phase of clients attempting to login"""
    verified = await client_recieve_handler(client_socket, loop, standby_time)
    if verified:
        if verified[0] == "veus" and verified[1] == "1" or verified[0] == "create_user" and verified[1] == "1":
            setup = await client_recieve_handler(client_socket, loop, recieve_timeout)
            try: 
                if setup[0] == "set_user" and setup[1]:
                    print("Login succesfull")
                    return setup[1]
            except Exception as e:
                print("Error: did not set client")
        print("USER NOT VERIFIED\n")

    return False

def create_user(user_data):
    username = user_data["username"]
    password = user_data["password"]
    hashed_password = utils.hash_password(password)
    if not username in users:
        users[username] = {}
        users[username]["username"] = username 
        users[username]["password"] = hashed_password
        users[username]["id"] = utils.gen_user_id()
        users[username]["permission_level"] = "basic"
        update_users_count()
        with open(users_path, "w") as file:
            json.dump(users, file, indent=4)  # Pretty print with indentation
        return 1
    else:
        print("User already exists")
        return False

async def client_handler(client_socket):
    loop = asyncio.get_event_loop()
    for attempts in range(3): #gives user 3 chances to login
        token = await login(client_socket, loop)
        if token:
            break

    if not token:
        print("Login failed")
        await safe_client_disconnect(client_socket, loop)
        return
    
    client_is_connected = True
    profile = get_user_profile(token)
   
    while client_is_connected:
        if profile:
            crh = await client_recieve_handler(client_socket, loop, recieve_timeout)
            if crh == "Lost client":
                profile["connection_error_count"] += 1
            else:
                profile["connection_error_count"] = 0
            
            if profile["connection_error_count"] == 3:
                print("Disconnected server to client")
                client_is_connected = False
                await safe_client_disconnect(client_socket, loop)

            if time.time() - profile["heartbeat"] > timeout:
                print("Client timout! Have not recieved a ping for too long!")
                client_is_connected = False
                await safe_client_disconnect(client_socket, loop)  
        else:
            print("Disconnected server to client, unrecognized session key or token")
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
