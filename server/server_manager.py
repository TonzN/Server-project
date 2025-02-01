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
client_capacity = config["user_capacity"] #to not connect more users than you can handle
func_keys = config["function_keys"]
recieve_timeout = 5 #timeout time for sending or recieving, gives time for users with high latency but also to not yield for too long
standby_time = 60*3 #time you allow someone to be trying to login
timeout = 15 #heartbeat timout time, if a user doesnt ping the server within this time it disconnects
user_profiles = {}
online_users = {}
#all functrions created must have an id passed
async def message_user(loop, data, tag, token):
    try:
        user = data[0]
        msg = data[1]
        if user in online_users:
            client_socket = online_users[user]
        else:
            return "user is not online"
        
        response = json.dumps({"data": [msg, "chat"]}) + "\n"
        await asyncio.wait_for(loop.sock_sendall(client_socket, response.encode()), recieve_timeout) #to send other users messages you need their socket
        return f"Sent message to {user}"
    
    except asyncio.TimeoutError:
        print("Socket timout, could not send or recieve in time")
        return "Did not send message"
    
    except Exception as e:
        print(f"could not recieve or send back to client or error with provided data {e}")
        return "Did nto send message"

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
                print("User {target_user} now has permission level {new_access_level}")
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

def show_online_users(msg, token):
    payload = get_user_profile(token)
    if payload:
        users = ""
        for user in online_users:
            users+=user+"  "
        return users
    else:
        return "invalid token"

def update_users_count(amount = 1):
    config["user_count"] += amount
    with open(config_path, "w") as file:
        json.dump(config, file, indent=4)  

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
    
def ping(msg, token): #updates users heartbeat time to maintain status health
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
    
    if not user in online_users: #prevents same user being connected from 2 sessions
        id = utils.gen_user_id()
        token = utils.generate_token(id)
        payload = utils.validate_token(token) 
        if payload: 
            """user profile manages a clients session data to keep it alive and info the server needs of the client, must not be sent to client"""
            session_key = payload["session_key"] #session key lets you access the users session profile, socket and username
            user_profiles[session_key] = {}
            user_profiles[session_key]["name"] = user 
            user_profiles[session_key]["id"] = payload["user_id"]
            user_profiles[session_key]["connection_error_count"] = 0
            user_profiles[session_key]["heartbeat"] = time.time()
            user_profiles[session_key]["socket"] = sock
            print(f"User: {user} connected to server")
            return token  #returns token to user, VERY important
        print("Weird things happens with token") #if something wrong happens here debug the server utils
    print("User already logged in")
    return False

async def safe_client_disconnect(client_socket, loop, username=False):
    response = "disconnect"
    if username:
        del online_users[username]
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
        try: #unpacks data 
            function = data["action"]
            msg = data["data"]
            tag = data["tag"]
            token = data["token"]
         #   print(f"Successfully unpacked data \n function: {function} \n data: {msg}")
        except Exception as e:
            print(msg, function, tag)
            print(f"Could not get function and msg: {e}")
            return
        
        """Server responses must be a dictionary: {"data": [content, tag]}"""
        if function in func_keys:  #checks if action requested exist as something the client can call for
            try:
                if function == "message_user": #functions with unique cases needs its own call
                    response =  str(await globals()[func_keys[function]](loop, msg, tag, token)) 
                elif token: #function requires authentication
                    response = str(globals()[func_keys[function]](msg, token)) 
                else: #function with not authentication
                    response = str(globals()[func_keys[function]](msg)) 

            except Exception as e: #sends back error message, this error means something wrong happened while running given function
                print(f"Function is not a valid server request: {e}\n Error at: {function}")
                response = json.dumps({"data": ["Attempted running function and failed.\n Check if the input passed is right", tag]}) + "\n"
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
            #for login sequence
            if function == "veus":
                return [function, msg]
            if function == "set_user":
                return [function, msg]
            if function == "create_user":
                return [function, msg]
            
            return function #returns function name back incase its needed

    except asyncio.TimeoutError:
        print("Socket timout, could not send or recieve in time")
        return "Lost client"
    
    except Exception as e:
        print(f"could not recieve or send back to client {e}")
        return "Lost client"

async def login(client_socket, loop):
    """Manages login phase of clients attempting to login, login has 2 phases, it expects verify user to be called first
    or register, then the next call HAS to be set_user to generate a token, if these steps cant be followed login will fail and server
    disconnects client"""
    verified = await client_recieve_handler(client_socket, loop, standby_time) #verified either returns False or a list 
    """Verified: [function, status] where "1" is success"""
    if verified:
        if verified[0] == "veus" and verified[1] == "1" or verified[0] == "create_user" and verified[1] == "1":
            setup = await client_recieve_handler(client_socket, loop, recieve_timeout) #setup [status, token]
            try: 
                if setup[1] == "False":
                    return False
                
                elif setup[0] == "set_user":
                    print("Login succesfull")
                    return setup[1] #returns token so the client handler knows the token
            except Exception as e:
                print("Error: did not set client")
        print("USER NOT VERIFIED\n")

    return False

def create_user(user_data): #userdata must be sent from the client as a dictionary with username and password
    username = user_data["username"]
    password = user_data["password"]
    hashed_password = utils.hash_password(password)
    if not username in users: #checks if user is registered
        """User data that has to be included when created, dont remove any of it but you can add"""
        users[username] = {} 
        users[username]["username"] = username 
        users[username]["password"] = hashed_password
        users[username]["id"] = utils.gen_user_id()
        users[username]["permission_level"] = "basic"
        update_users_count() #this updates user count to make sure next generated id is unique
        with open(users_path, "w") as file: 
            json.dump(users, file, indent=4)  #writes to users file
        return 1
    else:
        print("User already exists")
        return False

async def client_handler(client_socket):
    """Whenever you disconnect the client for whatever reason use safe client disconnect and await it since its async
    Login sequence HAS to go thru to make sure only registered users enters the main loop"""
    loop = asyncio.get_event_loop()
    for attempts in range(3): #gives user 3 chances to login
        token = await login(client_socket, loop)
        if token:
            break

    if not token:
        print("Login failed")
        await safe_client_disconnect(client_socket, loop)
        return
    #if token enters main loop
    client_is_connected = True 
    profile = get_user_profile(token) #fethes profile so the handler knows which user to pull from
    username = profile["name"]
    online_users[username] = client_socket
   
    while client_is_connected: #mainloop just makes sure the client health is safe and the recieve handler is called
        if profile:
            crh = await client_recieve_handler(client_socket, loop, recieve_timeout)
            if crh == "Lost client":
                profile["connection_error_count"] += 1
            else:
                profile["connection_error_count"] = 0
            
            if profile["connection_error_count"] == 3:
                print("Disconnected server to client")
                client_is_connected = False
                await safe_client_disconnect(client_socket, loop, username)

            if time.time() - profile["heartbeat"] > timeout:
                print("Client timout! Have not recieved a ping for too long!")
                client_is_connected = False
                await safe_client_disconnect(client_socket, loop, username)  
        else:
            print("Disconnected server to client, unrecognized session key or token")
            client_is_connected = False
            await safe_client_disconnect(client_socket, loop, username)

        time.sleep(0.02) #small delay of 20ms to not exhaust the system

async def run_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT)) 
        server_socket.listen(client_capacity)
        server_socket.setblocking(False) #must be false because its async
        loop = asyncio.get_event_loop() #evenloop for courotine 
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
