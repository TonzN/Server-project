from client.loads import *
import ast
import queue
import client.datastructures as ds
from client.thread_manager import *
from  client.client_utils import *

run_terminal = True
HEARTBEAT_INTERVAL = 3
short_lived_client = True

server_response_log = []

receieve_events = { #tag associated with where message has associated function
    "heartbeat":     asyncio.Event(),
    "join_protocol": asyncio.Event(),
    "main":          asyncio.Event(),
    "chat":          asyncio.Event(),
    "status_check": asyncio.Event(),
    "start_login": asyncio.Event(),
    "start_register": asyncio.Event(),
    "set_login_info": asyncio.Event(),
    "set_register_info": asyncio.Event(),
    "send_message": asyncio.Event(),
}

cross_comminication_queues = {
    "password": queue.Queue(),
    "username": queue.Queue(),
    "chat_message": queue.Queue(),
    "main": queue.Queue()
}

receieve_queue = { #tag associated with where message has associated function
    "heartbeat":     queue.Queue(),
    "join_protocol": queue.Queue(),
    "main":          queue.Queue(),
    "chat":          queue.Queue(),
    "status_check":  queue.Queue()
}

chat_data = {
    "path": None,
    "chat": None
}

signals = {
}

heartbeat_functions = {}

async def send_to_server(client_sock, msg, supress = False):
    if type(msg) is dict:
        try:
            await asyncio.wait_for(client_sock.send(json.dumps(msg).encode()), timeout=0.5)
            return True
        except Exception as e:
            if not supress:
                print(f"Could not send message to server {e}\n")
        except socket.timeout:
            print("Timed out trying to send message")
    else:
        if not supress:
            print("Invalid message format, please send as dictionary")

async def receive_from_server(client_sock, wait_for=2, expected_tag=None, supress=False, no_status_check=False, origin=False):
    """
    Asynchronously receives data from the server through the given client socket.
    Args:
        client_sock (asyncio.StreamReader): The client socket to receive data from.
        wait_for (int, optional): The timeout duration in seconds for waiting to receive data. Defaults to 2.
        expected_tag (str, optional): The expected tag to match the received message. Defaults to None.
        supress (bool, optional): If True, suppresses error messages. Defaults to False.
        no_status_check (bool, optional): If True, skips adding to the response log on error. Defaults to False.
        origin (bool, optional): Additional context for error messages. Defaults to False.
    Returns:
        bool: True if the message is successfully received and processed, False otherwise.
        None: If an error occurs or the operation times out.
    Raises:
        Exception: If an unexpected error occurs during the receiving process.
    """
    try:
        data = await asyncio.wait_for(client_sock.recv(), timeout=wait_for)
    except Exception as e:
        if not no_status_check:
            add_to_response_log(None)
        if not supress:
            print(f"Could not recieve from server: {e} | {origin}\n")
        return None
    except socket.timeout():
        if not no_status_check:
            add_to_response_log(None)
        if not supress:
             print(f"Timed out trying to receieve from server| {origin}")
        return None
    
    buffer = data.decode()
    while "\n" in buffer:
        message, buffer = buffer.split("\n", 1)

        msg = json.loads(message)
        content = msg["data"][0]
        tag = msg["data"][1]
        if tag == "chat":
            print(msg)
        add_to_response_log(content)


        try:
            if tag in receieve_queue:
                receieve_events[tag].set()
                receieve_queue[tag].put(content, block=False)
            else:
                print(f"invalid tag {tag} {content}")
                return False
        except Exception as e:
            print(f"1: Recieve from server error: {e}")

    return True

def full_pull_queue(_queue, timeout=0.1):
    if _queue in receieve_queue:
        while not receieve_queue[_queue].empty():
            try:
                recieved = receieve_queue[_queue].get(timeout=timeout)
                if type(recieved) == str:
                    try:
                        recieved = ast.literal_eval(recieved)
                    except Exception as e:
                     #   print(f"\nError at converting string to dict: {e}")
                        continue
                if recieved:
                    if "signal" in recieved:
                        if recieved["signal"] in signals:  
                            try:
                                if "data" in recieved:
                                    if type(recieved["data"]) == signals[recieved["signal"]][1]: #received content package
                                        signals[recieved["signal"]][0].emit(recieved["data"])       
                                elif type(recieved) == signals[recieved["signal"]][1]: #received datapackage
                                    signals[recieved["signal"]][0].emit(recieved)

                            except Exception as e:
                                print(f"Error at signal emit: {e}")
                                 
            except queue.Empty:
                break
    else:
        print("Full_pull_queue -> Invalid queue")

async def new_user_protocol(client_sock, user, password, token):    
    print("started registering")
    message = gen_message("create_user", {"username": user, "password": password}, "join_protocol", token=token)
    await send_to_server(client_sock, message)
    response = None
    try:
        if await receive_from_server(client_sock, supress=True):
            response = receieve_queue["join_protocol"].get(timeout=1)
            client.receieve_events["join_protocol"].clear()
    except asyncio.TimeoutError:
        print("timout error")
        return False
    except queue.Empty:
        print("empty queue")
        return False
    except Exception as e:
        print(f"{e}")
        return False   

    if response:
        if response == "1":
            message = {"username": user, "socket": str(client_sock), "password": password}
            msg = gen_message("set_user", message , "join_protocol", token=token)
            await send_to_server(client_sock, msg)
            success = None
            try:   
                if await receive_from_server(client_sock, supress=True):
                    success = receieve_queue["join_protocol"].get(timeout=1)
                    client.receieve_events["join_protocol"].clear()

            except queue.Empty:
                print("empty queue")
                return False
            
            except Exception as e:
                return False  
            
            if success:
                print(f"Welcome {user}")
                config["username"] = user
                config["successfull_login"] = True
                config["activate_heartbeat"] = True
                config["register_attempts"] = 0
                return 1
            else:
                print("Could not set up server profile, profile may already be setup or failed to receive token")
                return False
        else:
            print("\nUser already exists\n")

    else:
        print("Did not receieve from server or some unexpected error happebned")
        return False

def gen_message(action="", data="", tag="", token=None):
    """
    Generates a message dictionary with the given parameters.

    Args:
        action (str): The action to be performed. Default is an empty string.
        data (str): The data associated with the action. Default is an empty string.
        tag (str): A tag to categorize or identify the message. Default is an empty string.
        token (Any): An optional token for authentication or identification. Default is None.

    Returns:
        dict: A dictionary containing the provided parameters.
    """
    return {"action": action, "data":data, "tag": tag, "token": token}

def add_to_response_log(response):
    log_len = len(server_response_log)
    if log_len < 5:
        server_response_log.append(response)
    else:
        server_response_log.pop(0)
        server_response_log.append(response)

async def client_joined(client_sock, user, password, token):
    print("started client joining")
    message = gen_message("veus", {"username": user, "password": password}, "join_protocol", token=token)
    await send_to_server(client_sock, message)
    response = None
    try:
        if await receive_from_server(client_sock, supress=True):
            response = receieve_queue["join_protocol"].get(timeout=1)
            client.receieve_events["join_protocol"].clear()
    except asyncio.TimeoutError:
        print("timout error")
        return False
    except queue.Empty:
        print("empty queue")
        return False
    except Exception as e:
        print(f"{e}")       
        return False
    
    if response:    
        if response == "1":
            message = {"username": user, "socket": str(client_sock), "password": password}
            msg = gen_message("set_user", message , "join_protocol", token=token)
            await send_to_server(client_sock, msg)
            try:   
                if await receive_from_server(client_sock, supress=True):
                    success = receieve_queue["join_protocol"].get(timeout=1)
                    client.receieve_events["join_protocol"].clear()

            except queue.Empty:
                print("empty queue")
                return False
            
            except Exception as e:
                return False  
   
            if success == "True" :
                print(f"Welcome back {user}")
                config["username"] = user
                config["successfull_login"] = True
                config["login_attempts"] = 0
                return 1
            else:
                print("Could not set up server profile, profile may already be setup or failed to receive token")
                return False
        elif response == "2":
            print("\n Client is already logged in, please logout before attempting to login with another user.")
            return 2
        else:
            print(f"\nIncorrect username or password\n or server error: {response}")
            return False

    else:
        print("Did not receieve from server or some unexpected error happebned")
        return False

async def status_check(client_socket, token, force_ping = False):
    for response in server_response_log:
        if response == "disconnect":
            print("Warning: server disconnected client")
            return False
        
        if response == None or force_ping == True: #ping server
            for i in range(3):
                msg = gen_message("ping", "", "status_check", token)
                connection = await send_to_server(client_socket, msg, True)
                if connection:
                    response = receieve_queue["status_check"].get(timeout=1)
                    if response:
                        return True
                
                time.sleep(0.05)
            print("Could not ping server, no connection to server")
            return False
    
    return True
    #ping        

async def run_init(client_sock, login_signal):
    received = await receive_from_server(client_sock, supress=True)
    token = None
    if received:
        token = receieve_queue["join_protocol"].get(timeout=2)
        config["token"] = token
        login_signal.emit()
    return token

async def run_login(client_sock, stop_event, token):
    while not stop_event.is_set() and not receieve_events["set_login_info"].is_set() and not receieve_events["set_register_info"].is_set():
        time.sleep(0.3)
    
    user = cross_comminication_queues["username"].get()
    password = cross_comminication_queues["password"].get()
    if receieve_events["set_login_info"].is_set():
        joined = await client_joined(client_sock, user, password, token)
    elif receieve_events["set_register_info"].is_set():
        joined = await new_user_protocol(client_sock, user, password, token)

    if not joined:
        if config["login_attempts"] < 3:
            config["login_attempts"] += 1
            receieve_events["set_login_info"].clear()
            receieve_events["set_register_info"].clear()
            await run_login(client_sock, stop_event, token)
        else:
            print("Used up all login attempts")

async def heartbeat(client_sock):
    try:
        msg = gen_message("ping", "", "heartbeat", config["token"])
        sent = await send_to_server(client_sock, msg, True) 
    except Exception as e:
        print(f"Error at requesting ping from heartbeat {e}, sent: {sent}")
        return
    
    try:
        response = await receive_from_server(client_sock, wait_for=1, supress=False)
        if response:
            recieved = receieve_queue["heartbeat"].get(timeout=1)
            if not recieved:
                print("HEARTBEAT: reponse but did not fetch from queue")
                return False
            return recieved
        else:
            print("HEARTBEAT: no server response")
            return False
    
    except queue.Empty:
        return False

async def pulse_functions(client_socket):
    """
    Executes a series of heartbeat functions asynchronously using the provided client socket.

    Args:
        client_socket: The socket object used for client communication.

    Raises:
        Exception: If an error occurs during the execution of any heartbeat function.

    Notes:
        - If no heartbeat functions are registered, it prints a message indicating that the list is empty.
        - Each heartbeat function is expected to be an asynchronous function that takes the client_socket as an argument.
    """
    try:
        if len(heartbeat_functions) == 0:
            print("heartbeat functions empty")
        for funk_key in heartbeat_functions:
            await heartbeat_functions[funk_key](client_socket)
    except Exception as e:
        print(f"Error at pulse function: {e}")

async def run_client_mainloop(client_sock, stop_event):
    """
    Main loop for the client that handles sending and receiving messages, 
    as well as maintaining a heartbeat to ensure the connection is alive.
    Args:
        client_sock (asyncio.StreamWriter): The client's socket connection to the server.
        stop_event (threading.Event): An event to signal when to stop the main loop.
    Functionality:
        - Sends a heartbeat signal at regular intervals to keep the connection alive.
        - Sends messages from the client to the server when triggered.
        - Receives messages from the server and processes them.
        - Handles exceptions and errors that occur during message sending and receiving.
    Notes:
        - The function uses asyncio for asynchronous operations.
        - The heartbeat interval is defined by the constant HEARTBEAT_INTERVAL.
        - The function relies on several external variables and functions such as 
          `heartbeat`, `pulse_functions`, `send_to_server`, `recieve_from_server`, 
          `receieve_events`, `cross_comminication_queues`, and `signals`.
    """
    HEARTBEAT_TIME = time.time()
    while not stop_event.is_set():
        await asyncio.sleep(0.05)
        if time.time() - HEARTBEAT_TIME >= HEARTBEAT_INTERVAL:
            HEARTBEAT_TIME = time.time()
            heartbeat_attempt = await heartbeat(client_sock)
            await pulse_functions(client_sock)
            if not heartbeat_attempt:
                print("Unsuccesfull heartbeat")
        
        if receieve_events["send_message"].is_set():
            receieve_events["send_message"].clear()
            while not cross_comminication_queues["chat_message"].empty(): 
                try:
                    msg = cross_comminication_queues["chat_message"].get(timeout=0.1)
                except queue.Empty:
                    print("No chat message to send")
                    continue
                sent = await send_to_server(client_sock, msg, True)
                if sent:
                    if msg["data"][0] == "global":
                        signals["chat"][0].emit({"user": "[global] you", "message": msg["data"][1], "signal": "chat"})
                    else:
                        signals["chat"][0].emit({"user": "you", "message": msg["data"][1], "signal": "chat"})
            #   await receive_from_server(client_sock, wait_for=0.5, supress=True)
        try:
            await receive_from_server(client_sock, wait_for=0.15, supress=True)
            full_pull_queue("chat")
            if receieve_events["main"].is_set():
                while not cross_comminication_queues["main"].empty():
                    try:
                        msg = cross_comminication_queues["main"].get(timeout=0.1)
                    except queue.Empty:
                        print("No main request to send")
                        continue
                    sent = await send_to_server(client_sock, msg, True)
                    if not sent:
                        print("Could not send mainloop request")

                full_pull_queue("main")
                receieve_events["main"].clear()
                
        except Exception as e:
            print(f"Mainloop error: {e}")
                    
async def run_client(client_sock, login_signal, stop_event, main_menu_signal):
    if not config["token"]:
        token = await run_init(client_sock, login_signal)
        if token:
            await run_login(client_sock, stop_event, token)
        else:
            print("did not fetch token")

    if config["successfull_login"]:
        main_menu_signal.emit()
        await run_client_mainloop(client_sock, stop_event)

 