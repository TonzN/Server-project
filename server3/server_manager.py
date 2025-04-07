import threading
import json
import websockets
import time
import os
import server_utils as utils
from loads import *
from message_manager import *
from request_manager import *
from database_manager import *
from security_manager import *
from group_manager import *

HOST = config["HOST"]
PORT = config["PORT"]
client_capacity = config["user_capacity"] #to not connect more users than you can handle
func_keys = config["function_keys"]
recieve_timeout = 9 #timeout time for sending or recieving, gives time for users with high latency but also to not yield for too long
standby_time = 60*5 #time you allow someone to be trying to login
timeout = 30 #heartbeat timout time, if a user doesnt ping the server within this time it disconnects

#all functrions created must have an id passed

def set_client(userdata): #only used when a client joins! profile contains server data important to run clients
    try: 
        username = userdata["username"]
        sock = userdata["socket"]
        token = userdata["token"]
    except Exception as e:
        print(f"invalid userdata {e}")
        return False
    
    if verify_user(userdata) == 1:
        user = get_user(username)
        if not user: #prevents same user being connected from 2 sessions
            payload = utils.validate_token(token) 
            userfile = get_user_json_profile(username)
            if payload and users_file: 
                """user profile manages a clients session data to keep it alive and info the server needs of the client, must not be sent to client"""
                session_key = payload["session_key"] #session key lets you access the users session profile, socket and username
                profile = {}
                profile["name"] = username 
                profile["id"] = userfile["id"]
                profile["connection_error_count"] = 0
                profile["heartbeat"] = time.time()
                profile["socket"] = sock
                add_profile(session_key, profile)
                print(f"User: {username} connected to server")
                return True 
            
            print("Weird things happens with token") #if something wrong happens here debug the server utils
        print("User already logged in")
        return False
    else:
        return False

async def safe_client_disconnect(client_socket, loop, username, token):
    update_users_json_file()
        
    if username:
        user = get_user(username)
        if user:
            remove_user(username)
            print(f"User {username} disconnected")
    
    payload = utils.validate_token(token)
    if payload:
        session_key = payload["session_key"]
        remove_profile(session_key)
        utils.invalidate_token(token)

    await client_socket.close()
    #print("disconnect user...")
    return

async def client_recieve_handler(websocket, loop, recieve_timout):
    """
    Handles incoming messages from a client websocket connection.
    This function listens for messages from a client, processes the received data,
    and sends appropriate responses back to the client based on the requested action.
    Args:
        websocket (websockets.WebSocketServerProtocol): The websocket connection to the client.
        loop (asyncio.AbstractEventLoop): The event loop to run asynchronous tasks.
        recieve_timout (int): The timeout duration for receiving messages from the client.
    Returns:
        str or list: Returns the function name if the action is successfully processed,
                     or a list containing the function name and message for specific actions.
                     Returns "Client closed" if the connection is closed by the client,
                     or "lost client" if there is a timeout or other exception.
    Raises:
        websockets.exceptions.ConnectionClosed: If the websocket connection is closed.
        asyncio.TimeoutError: If receiving a message times out.
        Exception: If there is an error in receiving or sending data.
    """
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
            print(f"Could not get function and msg: {e}")
            return

        """Server responses must be a dictionary: {"data": [content, tag]}"""
        if function in func_keys:  #checks if action requested exist as something the client can call for
            try:
                if function == "message_user" or function == "message_group": #functions with unique cases needs its own call
                    response =  str(await globals()[func_keys[function]](loop, msg, tag, token)) 
                elif token: #function requires authentication
                    response = str(globals()[func_keys[function]](msg, token)) 
                else: #function with no authentication
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
        print("websocket.excpection lost connection")
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
        user = get_user_json_profile(username)
        if not user: #checks if user is registered, if not registered create user
            """User data that has to be included when created, dont remove any of it but you can add"""
            profile = {} 
            profile["username"] = username 
            profile["password"] = hashed_password
            profile["id"] = utils.gen_user_id()
            profile["permission_level"] = "basic"
            profile["chat_history"] = {"global":[]}
            profile["friends"] = {}
            profile["groups"] = {}
            profile["blacklist"] = {}
            profile["securitymode"] = "normal"
            profile["friend_requests"] = {}
            profile["preferences"] = {}
            add_user_json_profile(username, profile)
            update_users_count() #this updates user count to make sure next generated id is unique
            update_users_json_file()
            return 1
        else:
            print("User already exists")
            return False
    else:
        print("invalid token")
        return False

async def client_handler(websocket, path=None):
    """
    Handles a new WebSocket client connection.

    Parameters:
    websocket (websockets.WebSocketServerProtocol): The WebSocket connection to the client.
    path (str, optional): The path of the WebSocket connection. Defaults to None.

    Returns:
    None
    Whenever you disconnect the client for whatever reason use safe client disconnect and await it since its async.
    Login sequence HAS to go thru to make sure only registered users enters the main loop.
    """
    print(f"New WebSocket connection from {websocket.remote_address}, path: {path}")
    loop = asyncio.get_running_loop()
    timeout = 30
    if not hasattr(utils, 'generate_token'):
        raise ImportError(name='generate_token', msg="The 'generate_token' function is not available in 'utils'. Please check the import and initialization of 'utils'.")
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
    # If the token is valid, enter the main loop
    client_is_connected = True 
    profile = get_user_profile(token) #fethes profile so the handler knows which user to pull from
    if profile:
        username = profile["name"]
        add_user(username, websocket)
    else:
        await safe_client_disconnect(websocket, loop, None, token)
        return
    buffer_attemps = 3
   
    sleep_interval = 0.1  # initial sleep interval
    while client_is_connected: #mainloop just makes sure the client health is safe and the recieve handler is called
        start_time = time.time()
        if profile:
            crh = await client_recieve_handler(websocket, loop, recieve_timeout)
            if crh == "Client closed":
                buffer_attemps -= 1
            else:
                buffer_attemps = 3
                
            if buffer_attemps <= 0:
                client_is_connected = False
                await safe_client_disconnect(websocket, loop, username, token)
                print(f"Disconnecting {username}")

            if time.time() - profile["heartbeat"] >= timeout:
                print(f"Client: {profile["name"]} timout! Have not recieved a ping for too long!")
                client_is_connected = False
                await safe_client_disconnect(websocket, loop, username, token)  
        else:
            print("Disconnected server to client, unrecognized session key or token")
            client_is_connected = False
            await safe_client_disconnect(websocket, loop, username, token)

        elapsed_time = time.time() - start_time
        sleep_interval = max(0.01, min(0.1, sleep_interval * (1.1 if elapsed_time < sleep_interval else 0.9)))
        await asyncio.sleep(sleep_interval)  # dynamically adjusted sleep interva

async def run_server():
    """Starts the WebSocket server on a unique port."""
    port = PORT 
    server = await websockets.serve(client_handler, HOST, port, ping_interval=None, )
    print(f"WebSocket Server running on ws://{HOST}:{port} ")
    
    await server.wait_closed()  # Keeps the server running

async def main():
    await server_pool.initialize()
    db_connection = await test_db()
    if not db_connection:
        print("Could not connect to database, closing server")
        return
    
    pool = server_pool.get_pool("main_pool")
    print(await db_get_user_profile("Toni"))
    await run_server()

asyncio.run(main())