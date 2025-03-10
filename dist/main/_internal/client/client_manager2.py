from client.loads import *
import ast
import queue
import client.datastructures as ds
from client.thread_manager import *
from  client.client_utils import *

HOST = "ws://0.0.0.0:8765"  # The server's hostname or IP address
PORT = 12345  # The port used by the server

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
    "send_message": asyncio.Event()
}

cross_comminication_queues = {
    "password": queue.Queue(),
    "username": queue.Queue(),
    "chat_message": queue.Queue(),
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
            await client_sock.send(json.dumps(msg).encode())
            return True
        except Exception as e:
            if not supress:
                print(f"Could not send message to server {e}\n")
        except socket.timeout:
            print("Timed out trying to send message")
    else:
        if not supress:
            print("Invalid message format, please send as dictionary")

async def recieve_from_server(client_sock, wait_for=2, expected_tag=None, supress=False, no_status_check=False, origin=False):
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
        add_to_response_log(content)

        try:
            if tag in receieve_queue:
                receieve_events[tag].set()
                receieve_queue[tag].put(content)
                for match in signals:
                    if match == tag and signals[match][1] == type(content):
                        try:
                            signals[tag][0].emit(content)
                        except Exception as e:
                            print(f"2: recieve from server error: {e}")
            else:
                print(f"invalid tag {tag} {content}")
                return False
        except Exception as e:
            print(f"1: Recieve from server error: {e}")
            
        return True

async def new_user_protocol(client_sock, user, password, token):
    message = gen_message("create_user", {"username": user, "password": password, "token": token}, "join_protocol")
    await send_to_server(client_sock, message)
    response = receieve_queue["join_protocol"].get(timeout=1)

    if response:
        if response == "1":
            message = {"user": user, "socket": str(client_sock), "token": token}
            msg = gen_message("set_user", message , "join_protocol")
            await send_to_server(client_sock, msg)
            try:
                success = receieve_queue["join_protocol"].get(timeout=1)
            except queue.Empty:
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
    message = gen_message("veus", {"username": user, "password": password, "token": token}, "join_protocol")
    await send_to_server(client_sock, message)
    response = None
    try:
        if await recieve_from_server(client_sock, supress=True):
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
            message = {"user": user, "socket": str(client_sock), "token": token}
            msg = gen_message("set_user", message , "join_protocol")
            await send_to_server(client_sock, msg)
            try:   
                if await recieve_from_server(client_sock, supress=True):
                    success = receieve_queue["join_protocol"].get(timeout=1)
                    client.receieve_events["join_protocol"].clear()

            except queue.Empty:
                print("empty queue")
                return False
            
            except Exception as e:
                return False  
   
            if success != "False" :
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
            print("\nIncorrect username or password\n")
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
    received = await recieve_from_server(client_sock, supress=True)
    token = None
    if received:
        token = receieve_queue["join_protocol"].get(timeout=2)
        config["token"] = token
        login_signal.emit()
    return token

async def run_login(client_sock, stop_event, token):
    while not stop_event.is_set() and not receieve_events["set_login_info"].is_set():
        time.sleep(0.3)
    
    user = cross_comminication_queues["username"].get()
    password = cross_comminication_queues["password"].get()
    joined = await client_joined(client_sock, user, password, token)

    if not joined:
        if config["login_attempts"] < 3:
            config["login_attempts"] += 1
            await run_login(client_sock, stop_event, token)
            receieve_events["set_login_info"].clear()
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
        response = await recieve_from_server(client_sock, wait_for=1, supress=True)
        if response:
            recieved = receieve_queue["heartbeat"].get()
            if not recieved:
                return False
            return recieved
        else:
            return False
    
    except queue.Empty:
        return False

async def pulse_functions(client_socket):
    try:
        for funk_key in heartbeat_functions:
            await heartbeat_functions[funk_key](client_socket)
    except Exception as e:
        print(f"Error at pulse function: {e}")

async def run_client_mainloop(client_sock, stop_event):
    HEARTBEAT_TIME = time.time()
    while not stop_event.is_set():
        time.sleep(0.2)
        if time.time() - HEARTBEAT_TIME >= HEARTBEAT_INTERVAL:
            HEARTBEAT_TIME = time.time()
            heartbeat_attempt = await heartbeat(client_sock)
            await pulse_functions(client_sock)
            if not heartbeat_attempt:
                print("Unsuccesfull heartbeat")
        
        if receieve_events["send_message"].is_set():
            receieve_events["send_message"].clear()
            msg = cross_comminication_queues["chat_message"].get(timeout=1)
            await send_to_server(client_sock, msg, True)
            print("sent message")

        try:
            recieved = False
            recieved = await recieve_from_server(client_sock, wait_for=1, supress=True)
            if recieved:
                recieved = receieve_queue["main"].get(timeout=0.5)

            if not recieved:
                continue
        
        except queue.Empty:
            continue 

        except Exception as e:
            print(f"Mainloop error: {e}")
        
        try:
            recieved = ast.literal_eval(recieved)
        except:
            continue

        if recieved:
            if recieved["signal"] in signals:   
                if type(recieved["data"]) == signals[recieved["signal"]][1]:
                    signals[recieved["signal"]][0].emit(recieved["data"])       
            
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

 