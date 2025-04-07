import socket
import asyncio
import json
import time
import os
import threading
from loads import *
import datastructures as ds

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
    "chat":          asyncio.Queue()
}

receieve_events = { #tag associated with where message has associated function
    "heartbeat":     threading.Event(),
    "join_protocol": threading.Event(),
    "main":          threading.Event(),
    "chat":          threading.Event()
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

async def new_user_protocol(client_sock):
    print("Create user")
    user = input("Username: ")
    password = input("Password: ")
    message = gen_message("create_user", {"username": user, "password": password}, "join_protocol")
    send_to_server(client_sock, message)
    await asyncio.wait_for(asyncio.to_thread(receieve_events["join_protocol"].wait), timeout=5)
    response = await receieve_queue["join_protocol"].get()
    receieve_events["join_protocol"].clear()
    if response:
        if response == "1":
            message = {"user": user, "socket": str(client_sock)}
            msg = gen_message("set_user", message , "join_protocol")
            send_to_server(client_sock, msg)
            await asyncio.wait_for(asyncio.to_thread(receieve_events["join_protocol"].wait), timeout=5)
            token = await receieve_queue["join_protocol"].get()
            receieve_events["join_protocol"].clear()
            if token:
                print(f"Welcome {user}")
            else:
                print("Could not set up server profile, profile may already be setup or failed to receive token")
                return False
        else:
            print("\nUser already exists\n")
            new_user_protocol(client_sock)

    else:
        print("Did not receieve from server or some unexpected error happebned")
        return False

    return [user, token]

def gen_message(action="", data="", tag="", token=None):
    return {"action": action, "data":data, "tag": tag, "token": token}

def add_to_response_log(response):
    log_len = len(server_response_log)
    if log_len < 5:
        server_response_log.append(response)
    else:
        server_response_log.pop(0)
        server_response_log.append(response)

async def client_joined(client_sock, token):
    user = input("Username: ")
    password = input("Password: ")
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

def status_check(client_socket, token, force_ping = False):
    for response in server_response_log:
        if response == "disconnect":
            print("Warning: server disconnected client")
            return False
        
        if response == None or force_ping == True: #ping server
            for i in range(3):
                msg = gen_message("ping", "ping", "heartbeat", token)
                connection = send_to_server(client_socket, msg, True)
                if connection:
                    if recieve_from_server(client_socket) == "pong":
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
                print(f"Error recieving with server, bad connection or server is down. {e}")
                print("\n closing client")
                stop.set()
                return
        
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

async def client(): #activates a client
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock:
        try:
            client_sock.connect((HOST, PORT))
            print(f"Client connected.\n")
        except socket.timeout:
            print("Client timeout: attempted connecting for too long")
        except Exception as e:
            print(f"Client did not connect: {e}\n")
            return  
        data = {"messages":[]}
        
        rec_stop = threading.Event()
        rec_thread = threading.Thread(target=receive_thread, args=(client_sock, rec_stop), daemon=True)
        rec_thread.start()

        valid_action = False
        joined = False
        join_attempts = 3

        while not valid_action:
            login = input("Login or Register: ")
            if login.lower() == "login":
                joined = await client_joined(client_sock)
                if not joined:
                    join_attempts -= 1
                if joined or join_attempts == 0:
                    valid_action = True    
            elif login.lower() == "register":
                joined = await new_user_protocol(client_sock)
                if not joined:
                    join_attempts -= 1
                if joined:
                    valid_action = True
            elif login.lower() == "exit":
                valid_action = True

        if joined:
            user = joined[0]
            token = joined[1]
            with open(f"{user}_chat.json", "w") as file:
                json.dump(data, file, indent=4)
            chat_data["path"] = f"{user}_chat.json"
            with open(chat_data["path"], 'r') as file:
                chat_data["chat"] = json.load(file)
        else:
            print("Unsuccesfull login")
            safe_close(client_sock, rec_thread, rec_stop, None, None)
            return
      
        stop_event = threading.Event()
        heartbeat_thread = threading.Thread(target=heartbeat, args=(client_sock, stop_event, token), daemon=True)
        heartbeat_thread.start()
        
        config["active_heartbeat"] = True
        chatting = False
    
        while True:
            #status = status_check(client_sock, token)
            status = True
            if status == False or config["active_heartbeat"] == False:
                safe_close(client_sock, rec_thread, rec_stop, heartbeat_thread, stop_event)
                print(f"Disconnected client {user}, lost connection to server\n")
                break

            ask = input("Cmd: ")
            if ask == "exit" or rec_stop.is_set():
                safe_close(client_sock, rec_thread, rec_stop, heartbeat_thread, stop_event)
                print(f"Goodbye {user}")
                break
            if ask == "chat" and chatting == False:
                open_chat()
                chatting = True
                continue

            inputs = input("How many inputs: ")
            msg_content = []
            try: 
                int(inputs)
            except Exception as e:
                print(e)
                continue
        
            for i in range(int(inputs)):
                inp = input("Input: ")
                if inp == "exit_input":
                    break
                msg_content.append(inp)

            msg = gen_message(ask, msg_content, "main", token)
            send_to_server(client_sock, msg)
            await asyncio.wait_for(asyncio.to_thread(receieve_events["main"].wait), timeout=5)
            response = await receieve_queue["main"].get()
            receieve_events["main"].clear()
            if response:
                print("Server response:", response)
                
            time.sleep(0.02)
      
def main():
    asyncio.run(client())

auto_connect = False

while run_terminal:
    if auto_connect:
        main()
    time.sleep(0.1)
    server_response_log = []    

    cmd = input("command: ")
    if cmd == "close":
        run_terminal = False

    if cmd == "connect":
        main()
        