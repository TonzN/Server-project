from client.loads import *
import client.datastructures as ds

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 12345  # The port used by the server

run_terminal = True
HEARTBEAT_INTERVAL = 5
short_lived_client = True

server_response_log = []
receieve_queue = { #tag associated with where message has associated function
    "heartbeat":     asyncio.Queue(),
    "join_protocol": asyncio.Queue(),
    "main":          asyncio.Queue(),
    "chat":          asyncio.Queue(),
    "status_check":  asyncio.Queue()
}

receieve_events = { #tag associated with where message has associated function
    "heartbeat":     threading.Event(),
    "join_protocol": threading.Event(),
    "main":          threading.Event(),
    "chat":          threading.Event(),
    "status_check": threading.Event()
}

chat_data = {
    "path": None,
    "chat": None
}

def send_to_server(client_sock, msg, supress = False):
    if type(msg) is dict:
        try:
            client_sock.sendall(json.dumps(msg).encode())
            return True
        except Exception as e:
            if not supress:
                print(f"Could not send message to server {e}\n")
        except socket.timeout:
            print("Timed out trying to send message")
    else:
        if not supress:
            print("Invalid message format, please send as dictionary")

async def recieve_from_server(client_sock, wait_for=5, expected_tag=None, supress=False, no_status_check=False, origin=False):
    client_sock.settimeout(wait_for)
    try:
        data = client_sock.recv(1024)
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

        if tag in receieve_queue:
            receieve_queue[tag].put_nowait(content)
            receieve_events[tag].set()
            
            if tag == "chat":
                receieve_events[tag].clear()
                await get_incoming_messages()
        else:
            print(f"invalid tag {tag} {content}")
            return False
        
        return True

async def new_user_protocol(client_sock, user, password, token):
    message = gen_message("create_user", {"username": user, "password": password, "token": token}, "join_protocol")
    send_to_server(client_sock, message)
    await asyncio.wait_for(asyncio.to_thread(receieve_events["join_protocol"].wait), timeout=5)
    response = await receieve_queue["join_protocol"].get()
    receieve_events["join_protocol"].clear()

    if response:
        if response == "1":
            message = {"user": user, "socket": str(client_sock), "token": token}
            msg = gen_message("set_user", message , "join_protocol")
            send_to_server(client_sock, msg)
            await asyncio.wait_for(asyncio.to_thread(receieve_events["join_protocol"].wait), timeout=5)
            success = await receieve_queue["join_protocol"].get()
            receieve_events["join_protocol"].clear()
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
    message = gen_message("veus", {"username": user, "password": password, "token": token}, "join_protocol")
    send_to_server(client_sock, message)
    await asyncio.wait_for(asyncio.to_thread(receieve_events["join_protocol"].wait), timeout=5)
    response = await receieve_queue["join_protocol"].get()
    receieve_events["join_protocol"].clear()
    
    if response:    
        if response == "1":
            message = {"user": user, "socket": str(client_sock), "token": token}
            msg = gen_message("set_user", message , "join_protocol")
            send_to_server(client_sock, msg)
            await asyncio.wait_for(asyncio.to_thread(receieve_events["join_protocol"].wait), timeout=5)
            success = await receieve_queue["join_protocol"].get()
            receieve_events["join_protocol"].clear()
   
            if success != "False":
                print(f"Welcome back {user}")
                config["username"] = user
                config["successfull_login"] = True
                config["activate_heartbeat"] = True
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
        print("attempting status check")
        if response == "disconnect":
            print("Warning: server disconnected client")
            return False
        
        if response == None or force_ping == True: #ping server
            for i in range(3):
                msg = gen_message("ping", "", "status_check", token)
                connection = send_to_server(client_socket, msg, True)
                if connection:
                    await asyncio.wait_for(asyncio.to_thread(receieve_events["status_check"].wait), timeout=5)
                    response = await receieve_queue["status_check"].get()
                    receieve_events["status_check"].clear()
                    if response:
                        return True
                
                time.sleep(0.05)
            print("Could not ping server, no connection to server")
            return False
    
    return True
    #ping

async def async_heartbeat(client_socket, stop, token):
    while not stop.is_set():
        msg = gen_message("ping", "", "heartbeat", token)
        sent = send_to_server(client_socket, msg, True) 
        try:
            await asyncio.wait_for(asyncio.to_thread(receieve_events["heartbeat"].wait), timeout=5)
            recieved = await receieve_queue["heartbeat"].get()
            receieve_events["heartbeat"].clear()
        except asyncio.TimeoutError:
            continue
            
        if not sent or not recieved:
            print("Heartbeat failed. Server may be down.")
            print(f"sent: {sent} recieved {recieved}")
            stop.set()
            status = status_check(client_socket, True)
            if not status:
                config["active_heartbeat"] = False
                break
    
        time.sleep(HEARTBEAT_INTERVAL)

def heartbeat(client_socket, stop, token):
    """cheesy solution to do async and threading"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)  # Attach event loop to this thread
    loop.run_until_complete(async_heartbeat(client_socket, stop, token))  # Run async function
    
async def async_receive_thread(client_sock, stop):
    counter = 0
    while not stop.is_set():
        try:
            await recieve_from_server(client_sock, 1, None, True, True)
            counter = 0
        except Exception as e:
            counter += 1
            if counter >= 3:
                connected = status_check(client_sock, config["token"])
                if not connected:
                    print(f"Error recieving with server, bad connection or server is down. {e}")
                    print("\n closing client")
                    stop.set()
                    return
                else:
                    counter = 0
        
        await asyncio.sleep(0.1)  # Allow checking the stop condition regularly

def receive_thread(client_socket, stop):
    """cheesy solution to do async and threading"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)  # Attach event loop to this thread
    try:
        loop.run_until_complete(async_receive_thread(client_socket, stop))  # Run async function
    finally:
        loop.close()  # Make sure to close the event loop properly when done
        return

async def get_incoming_messages():
    message = await receieve_queue["chat"].get()
    if message:
        with open(chat_data["path"], 'r') as file:
                chat_data["chat"] = json.load(file)

        chat_data["chat"]["messages"].append(message)
        with open(chat_data["path"], "w") as file:
            json.dump(chat_data["chat"], file, indent=4) 

    time.sleep(0.2)

def open_chat():
    path = chat_data["path"]
    os.system(f"start cmd /K python C:/Users/LAB/Documents/super-server-project/client/chat.py {path}")

def safe_close(client_sock, recieve, rec_stop, heartbeat, heart_stop):
    if recieve:
        rec_stop.set()
        print("waiting for recieve_thread to end")
        recieve.join()  # Wait for the thread to finish
    if heartbeat:
        heart_stop.set()
        print("waiting for heartbeat to end")
        heartbeat.join()

    client_sock.close()
    
def run_client(client_sock):
    
    stop_event = threading.Event()
    connected = True

    while connected:
        if config["successfull_login"]:
            if config["activate_heartbeat"] == True:
                heartbeat_thread = threading.Thread(target=heartbeat, args=(client_sock, stop_event, config["token"]), daemon=True)
                heartbeat_thread.start()
                config["activate_heartbeat"] = False

        time.sleep(0.25)
