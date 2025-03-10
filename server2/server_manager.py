import threading
import asyncio
import json
import websockets
import time
import os
import server_utils as utils
from loads import *

HOST = config["HOST"]
PORT = config["PORT"]
client_capacity = config["user_capacity"] #to not connect more users than you can handle
func_keys = config["function_keys"]
recieve_timeout = 9 #timeout time for sending or recieving, gives time for users with high latency but also to not yield for too long
standby_time = 60*5 #time you allow someone to be trying to login
timeout = 30 #heartbeat timout time, if a user doesnt ping the server within this time it disconnects
user_profiles = {}
online_users = {}
#all functrions created must have an id passed
groups = {"global"}

async def message_group(loop, data, tag, token):
    try:
        profile = get_user_profile(token)
        if profile:
            group = data[0]
            msg = data[1]
            if group in groups:
                if group == "global":
                    for user in online_users:
                        if user != profile["name"]:
                            client_socket = online_users[user]
                            response = json.dumps({"data": [{"user": "[global]"+profile["name"], "message": msg}, "chat"]}) + "\n"
                            await client_socket.send(response.encode()) #to send other users messages you need their socket
                    return f"Sent message to {group}"
            else:
                return "invalid group"
        else:
            return "invalid token"
    
    except asyncio.TimeoutError:
        print("Socket timout, could not send or recieve in time")
        return "Did not send message"
    
    except Exception as e:
        print(f"could not recieve or send back to group or error with provided data {e}")
        return "Did not send message"

async def message_user(loop, data, tag, token):
    try:
        profile = get_user_profile(token)
        if profile:
            user = data[0]
            msg = data[1]
            if user in online_users:
                client_socket = online_users[user]
            else:
                return "user is not online"
            
            response = json.dumps({"data": [{"user": profile["name"], "message": msg}, "chat"]}) + "\n"
            await client_socket.send(response.encode()) #to send other users messages you need their socket
            return f"Sent message to {user}"
        else:
            return "invalid token"
    
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
                print(f"User {target_user} now has permission level {new_access_level}")
                return "Success"
            else:
                return "Not high enough access level to do this"
        else:
            return "Userprofile is missing"
    else:
        return "Invalid token"

def kill_server(msg, token):
    user = get_user_profile(token)
    if user:
        username = user["name"]
        id = user["id"]
        if users[username]["permission_level"] == "admin":
            print(f"User {username}#{id} killed the server!!")
            print(msg)
            os._exit(0)
        else:
            return "Not high enough access level"
    return "Unverfied token"

def get_id(msg, token):
    user = get_user_profile(token)
    if user:
        username = user["name"]
        id  = user["id"]
        return f"#{id}"
    
    return "Unverfied token"

def get_permission_level(msg, token):
    user = get_user_profile(token)
    if user["id"]:
        username = user["name"]
        permission_level = users[username]["permission_level"]
        return permission_level
    
    return "Unverfied token"

def show_online_users(msg, token):
    payload = get_user_profile(token)
    signal = msg
    if payload:
        users = {"data": []}
        for user in online_users:
            users["data"].append(user)
        return {"data": users, "signal": signal}
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
        token = user_data["token"]

    except Exception as e:
        print("invalid data provided")
        return 0
    if username in users:
        profile = get_user_profile(token)
        if not profile:
            if utils.verify_password(users[username]["password"], password):
                return 1
            else:
                return 0
        return 2
    return 0

def get_user_profile(token):
    payload = utils.validate_token(token)
    if payload:
        session_key = payload["session_key"]
        if session_key in user_profiles:
            return user_profiles[session_key]
        else:
            return False
    else:
        print(f"INVALID TOKEN {token}")
        return False
    
def ping(msg, token=None): #updates users heartbeat time to maintain status health
    if token:
        user = get_user_profile(token)
        if user:
            if msg == "ping":
                print("ping")
            user["heartbeat"] = time.time()
            return "pong"

def set_client(userdata)    : #only used when a client joins! profile contains server data important to run clients
    try: 
        user = userdata["user"]
        sock = userdata["socket"]
        token = userdata["token"]
    except Exception as e:
        print(f"invalid userdata {user} {sock} {e}")
        return False
    
    if not user in online_users: #prevents same user being connected from 2 sessions
        payload = utils.validate_token(token) 
        if payload: 
            """user profile manages a clients session data to keep it alive and info the server needs of the client, must not be sent to client"""
            session_key = payload["session_key"] #session key lets you access the users session profile, socket and username
            user_profiles[session_key] = {}
            user_profiles[session_key]["name"] = user 
            user_profiles[session_key]["id"] = users[user]["id"]
            user_profiles[session_key]["connection_error_count"] = 0
            user_profiles[session_key]["heartbeat"] = time.time()
            user_profiles[session_key]["socket"] = sock
            print(f"User: {user} connected to server")
            return True 
        
        print("Weird things happens with token") #if something wrong happens here debug the server utils
    print("User already logged in")
    return False

async def safe_client_disconnect(client_socket, loop, username, token):
    with open(users_path, 'w') as file:
        json.dump(users, file, indent=4)
        
    response = "disconnect"
    if username:
        if username in online_users:
            online_users[username] = None
            del online_users[username]
    try: 
        await client_socket.send(json.dumps(response).encode())
    except Exception as e:
        pass
    
    payload = utils.validate_token(token)
    if payload:
        session_key = payload["session_key"]
        if session_key in user_profiles:
            del user_profiles[session_key]
        utils.invalidate_token(token)

    await client_socket.close()
    #print("disconnect user...")
    return

async def client_recieve_handler(websocket, loop, recieve_timout):
    try:
        data = await asyncio.wait_for(websocket.recv(), timeout=recieve_timout) #format: action: ... data: ...
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
                if function == "message_user" or function == "message_group": #functions with unique cases needs its own call
                    response =  str(await globals()[func_keys[function]](loop, msg, tag, token)) 
                elif token: #function requires authentication
                    response = str(globals()[func_keys[function]](msg, token)) 
                else: #function with not authentication
                    response = str(globals()[func_keys[function]](msg)) 

            except Exception as e: #sends back error message, this error means something wrong happened while running given function
                print(f"Function is not a valid server request: {e}\n Error at: {function}")
                response = json.dumps({"data": ["Attempted running function and failed.\n Check if the input passed is right", tag]}) + "\n"
                await websocket.send(response.encode())
                return False
        else:
            response = json.dumps({"data": ["invalid action", tag]}) + "\n"
            await websocket.send(response.encode())
            return False

        if response:
            msg = response
            response = json.dumps({"data": [response, tag]}) + "\n"
            await websocket.send(response.encode())
            #for login sequence
            if function == "veus":
                return [function, msg]
            if function == "set_user":
                return [function, msg]
            if function == "create_user":
                return [function, msg]
            
            return function #returns function name back incase its needed
        
    except websockets.exceptions.ConnectionClosed:
        print("user disconnect")
        return "Client closed"

    except asyncio.TimeoutError:
        #print("Socket timout, could not send or recieve in time")
        return "lost client"
    
    except Exception as e:
        print(f"could not recieve or send back to client {e}")
        return "Lost client"

async def send_to_user(websocket, loop, message, tag, timeout):
    try:
        response = json.dumps({"data": [message, tag]}) + "\n"
        await websocket.send(response.encode())
        return True

    except asyncio.TimeoutError:
        print("Socket timout, could not send or recieve in time")
        return "Lost client"
    
    except Exception as e:
        print(f"could not recieve or send back to client {e}")
        return "Lost client"
    
async def login(websocket, loop):
    """Manages login phase of clients attempting to login, login has 2 phases, it expects verify user to be called first
    or register, then the next call HAS to be set_user to generate a token, if these steps cant be followed login will fail and server
    disconnects client"""
    verified = await client_recieve_handler(websocket, loop, standby_time) #verified either returns False or a list 
    """Verified: [function, status] where "1" is success"""
    if verified:
        if verified == "ping":
            return "ignore"
        
        if verified[0] == "veus" and verified[1] == "1" or verified[0] == "create_user" and verified[1] == "1":
            setup = await client_recieve_handler(websocket, loop, recieve_timeout) #setup [status, token]
            try: 
                if setup[1] == "False":
                    return False
                
                elif setup[0] == "set_user":
                    print("Login succesfull")
                    return True 
            except Exception as e:
                print("Error: did not set client")
        print("USER NOT VERIFIED\n")

    return False

def create_user(user_data): #userdata must be sent from the client as a dictionary with username and password
    username = user_data["username"]
    password = user_data["password"]
    token = user_data["token"]
    hashed_password = utils.hash_password(password)
    if utils.validate_token(token):
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
    else:
        print("invalid token")
        return False

async def client_handler(websocket, path=None):
    """Whenever you disconnect the client for whatever reason use safe client disconnect and await it since its async
    Login sequence HAS to go thru to make sure only registered users enters the main loop"""
    print(f"New WebSocket connection from {websocket.remote_address}, path: {path}")

    loop = asyncio.get_event_loop()
    token = utils.generate_token()
    success = False
    sent_token = await send_to_user(websocket, loop, token, "join_protocol", 5)
    attempts = 3
    if sent_token:
        while attempts >= 0: #gives user 3 chances to login
            attempts -= 1
            success = await login(websocket, loop)
            if success == "ignore":
                attempts += 1

            if success and success != "ignore":
                break
    else:
        print("Did not send client token")

    if not success:
        print("Login failed")
        await safe_client_disconnect(websocket, loop, None, token)
        return
    #if token enters main loop
    client_is_connected = True 
    profile = get_user_profile(token) #fethes profile so the handler knows which user to pull from
    username = profile["name"]
    online_users[username] = websocket
   
    while client_is_connected: #mainloop just makes sure the client health is safe and the recieve handler is called
        if profile:
            crh = await client_recieve_handler(websocket, loop, recieve_timeout)
            if crh == "Client closed":
                client_is_connected = False
                await safe_client_disconnect(websocket, loop, username, token)
            if time.time() - profile["heartbeat"] > timeout:
                print("Client timout! Have not recieved a ping for too long!")
                client_is_connected = False
                await safe_client_disconnect(websocket, loop, username, token)  
        else:
            print("Disconnected server to client, unrecognized session key or token")
            client_is_connected = False
            await safe_client_disconnect(websocket, loop, username, token)

        time.sleep(0.02) #small delay of 20ms to not exhaust the system

async def run_server():
    """Starts the WebSocket server."""
    server = await websockets.serve(client_handler, HOST, PORT)
    print(f"WebSocket Server running on ws://{HOST}:{PORT}")
    
    await server.wait_closed()  # Keeps server running
    print("closing server")

    
async def main():
    await run_server()

asyncio.run(main())
