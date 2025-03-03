from client.loads import *
import ast
import client.datastructures as ds

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 12345  # The port used by the server

run_terminal = True
HEARTBEAT_INTERVAL = 2.5
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

signals = {
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

async def recieve_from_server(client_sock, wait_for=2, expected_tag=None, supress=False, no_status_check=False, origin=False):
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
            for match in signals:
                if match == tag:
                    signals[tag].emit(content)
                    receieve_events[tag].clear()
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
    try:
        await asyncio.wait_for(asyncio.to_thread(receieve_events["join_protocol"].wait), timeout=1)
    except Exception as e:
        receieve_events["join_protocol"].set()
        receieve_events["join_protocol"].clear()
        return False
    response = await receieve_queue["join_protocol"].get()
    receieve_events["join_protocol"].clear()
    
    if response:    
        if response == "1":
            message = {"user": user, "socket": str(client_sock), "token": token}
            msg = gen_message("set_user", message , "join_protocol")
            send_to_server(client_sock, msg)
            try:
                await asyncio.wait_for(asyncio.to_thread(receieve_events["join_protocol"].wait), timeout=1)
            except Exception as e:
                receieve_events["join_protocol"].set()
                receieve_events["join_protocol"].clear()
                return False
            
            success = await receieve_queue["join_protocol"].get()
            receieve_events["join_protocol"].clear()
   
            if success != "False":
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
        if not stop.is_set() or config["stop"] == True:
            time.sleep(HEARTBEAT_INTERVAL)
    
        msg = gen_message("ping", "", "heartbeat", token)
        sent = send_to_server(client_socket, msg, True) 
        try:
            success = await asyncio.wait_for(asyncio.to_thread(receieve_events["heartbeat"].wait), timeout=1)
            recieved = await receieve_queue["heartbeat"].get()
            receieve_events["heartbeat"].clear()
            if not success:
                receieve_events["heartbeat"].set()
                receieve_events["heartbeat"].clear()

        except asyncio.TimeoutError:
            receieve_events["heartbeat"].set()
            receieve_events["heartbeat"].clear()
            continue
            
        if not sent or not recieved:
            print("Heartbeat failed. Server may be down.")
            print(f"sent: {sent} recieved {recieved}")
            stop.set()
            status = status_check(client_socket, True)
            if not status:
                break
    print("heartbeat ended")

def heartbeat(client_socket, stop, token):
    """cheesy solution to do async and threading"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)  # Attach event loop to this thread
    try:
        loop.run_until_complete(async_heartbeat(client_socket, stop, token))  # Run async function
    finally:
        loop.close()
        return
    
async def async_receive_thread(client_sock, stop):
    counter = 0
    while not stop.is_set():
        try:
            await recieve_from_server(client_sock, 1, None, True, True)
            counter = 0
        except Exception as e:
            counter += 1
            if counter >= 10:
                connected = await status_check(client_sock, config["token"])
                if not connected:
                    print(f"Error recieving with server, bad connection or server is down. {e}")
                    print("\n closing client")
                    stop.set()
                    return
                else:
                    counter = 0
        
        await asyncio.sleep(0.1)  # Allow checking the stop condition regularly
    print("recieve ended")

def receive_thread(client_socket, stop):
    """cheesy solution to do async and threading"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)  # Attach event loop to this thread
    try:
        loop.run_until_complete(async_receive_thread(client_socket, stop))  # Run async function
    finally:
        loop.close()  # Make sure to close the event loop properly when done
        return
    
async def run_client(client_sock, heartbeat_stop):
    connected = True

    while connected:

        if heartbeat_stop.is_set() or config["stop"] == True:
            connected = False
            return

        if config["successfull_login"]:   
            try:
                success = await asyncio.wait_for(asyncio.to_thread(receieve_events["main"].wait), timeout=1)
                recieved = await receieve_queue["main"].get()
                receieve_events["main"].clear()
                if not success:
                    receieve_events["main"].set()
                    receieve_events["main"].clear()
                    continue

            except asyncio.TimeoutError as e:
                receieve_events["main"].set()
                receieve_events["main"].clear()
                continue

            except Exception as e:
                receieve_events["main"].set()
                receieve_events["main"].clear()
                return
            
            try:
                recieved = ast.literal_eval(recieved)
            except:
                continue

            if recieved:
                if recieved["signal"] in signals:
                    signals[recieved["signal"]].emit(recieved["data"])

        time.sleep(0.25)
