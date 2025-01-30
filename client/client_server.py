import socket
import asyncio
import json
import time
import os
import threading
import datastructures as ds

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 12345  # The port used by the server

config_path = "client/client_config.json" #incase path changes
chat_path = "client/chats.json"
run_terminal = True
HEARTBEAT_INTERVAL = 5
short_lived_client = True

server_response_log = []
receieve_queue = { #tag associated with where message has associated function
    "heartbeat": ds.Queue(),
    "join_protocol": ds.Queue(),
    "main": ds.Queue(),
    "chat": ds.Queue()
}

#load paths
try: #attempt fetching configs
    with open(config_path, 'r') as file:
        config = json.load(file)
except FileNotFoundError:
    print(f"Error: The file '{config_path}' does not exist.")
except json.JSONDecodeError:
    print(f"Error: The file '{config_path}' contains invalid JSON.")
except PermissionError:
    print(f"Error: Permission denied while accessing '{config_path}'.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
try: #attempt fetching configs
    with open(chat_path, 'r') as file:
        chat = json.load(file)
except FileNotFoundError:
    print(f"Error: The file '{chat_path}' does not exist.")
except json.JSONDecodeError:
    print(f"Error: The file '{chat_path}' contains invalid JSON.")
except PermissionError:
    print(f"Error: Permission denied while accessing '{chat_path}'.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")


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

def recieve_from_server(client_sock, expected_tag=None, supress=False, chat_rec=False, origin=False):
    try:
        data = client_sock.recv(1024)
    except Exception as e:
        if not chat_rec:
            add_to_response_log(None)
        if not supress:
            print(f"Could not recieve from server: {e} | {origin}\n")
        return None
    except socket.timeout():
        if not chat_rec:
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
            receieve_queue[tag].Push(content)
            if expected_tag: #incase heartbeat and some other receieve requests happens at the same time they may mistmatch, therefor it will call again
                if expected_tag[0] != tag and expected_tag[1] < 3:
                    expected_tag[1] += 1
                    recieve_from_server(client_sock, expected_tag)
        else:
            print(f"invalid tag {tag} {content}")
            return False
        
        return True

def new_user_protocol(client_sock):
    print("Create user")
    user = input("Username: ")
    password = input("Password: ")
    message = gen_message("create_user", {"username": user, "password": password}, "join_protocol")
    send_to_server(client_sock, message)
    got_response = recieve_from_server(client_sock, ["join_protocol", 0])
    
    if got_response:
        response = receieve_queue["join_protocol"].Pop()
        if response == "1":
            message = {"user": user, "socket": str(client_sock)}
            msg = gen_message("set_user", message , "join_protocol")
            send_to_server(client_sock, msg)
            got_response = recieve_from_server(client_sock, ["join_protocol", 0])
            if got_response:
                token = receieve_queue["join_protocol"].Pop()
                if token:
                    print(f"Welcome {user}")
                else:
                    print("Could not set up server profile, profile may already be setup")
                    return False

            else:
                print("Did not get set user or server disconnected")
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

def client_joined(client_sock):
    user = input("Username: ")
    password = input("Password: ")
    message = gen_message("veus", {"username": user, "password": password}, "join_protocol")
    send_to_server(client_sock, message)
    got_response = recieve_from_server(client_sock, ["join_protocol", 0])
    
    if got_response:
        response = receieve_queue["join_protocol"].Pop()
        if response == "1":
            message = {"user": user, "socket": str(client_sock)}
            msg = gen_message("set_user", message , "join_protocol")
            send_to_server(client_sock, msg)
            got_response = recieve_from_server(client_sock, ["join_protocol", 0])
            if got_response:
                token = receieve_queue["join_protocol"].Pop()
                if token != "False":
                    print(f"Welcome back {user}")
                else:
                    print("Could not set up server profile, profile may already be setup")
                    return False

            else:
                print("Did not get set user or server disconnected")
                return False
        else:
            print("\nIncorrect username or password\n")
            return False

    else:
        print("Did not receieve from server or some unexpected error happebned")
        return False

    return [user, token]

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

def heartbeat(client_socket, stop, token):
    while not stop.is_set():
        msg = gen_message("ping", "", "heartbeat", token)
        sent = send_to_server(client_socket, msg, True) 
        recieved = recieve_from_server(client_socket)
        if not sent and recieved:
            print("Heartbeat failed. Server may be down.")
            stop.set()
            status = status_check(client_socket, True)
            if not status:
                config["active_heartbeat"] = False
                break
        else:
            receieve_queue["heartbeat"].Pop()
        time.sleep(HEARTBEAT_INTERVAL)

def get_incoming_messages(client_socket, stop):
    os.system("start cmd /K python C:/Users/LAB/Documents/super-server-project/client/chat.py")
    while not stop.is_set():
        recieved = recieve_from_server(client_socket, None, True, True, "chat")
        if recieved:
            message = receieve_queue["chat"].Pop()
            chat["messages"].append(message)
            with open(chat_path, "w") as file:
                json.dump(chat, file, indent=4) 

        time.sleep(0.2)
    
def client(): #activates a client
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock:
        client_sock.settimeout(5)
        try:
            client_sock.connect((HOST, PORT))
            print(f"Client connected.\n")
        except socket.timeout:
            print("Client timeout: attempted connecting for too long")
        except Exception as e:
            print(f"Client did not connect: {e}\n")
            return  

        valid_action = False
        joined = False
        join_attempts = 3

        while not valid_action:
            login = input("Login or Register: ")
            if login.lower() == "login":
                joined = client_joined(client_sock)
                if not joined:
                    join_attempts -= 1
                if joined or join_attempts == 0:
                    valid_action = True    
            elif login.lower() == "register":
                joined = new_user_protocol(client_sock)
                if not joined:
                    join_attempts -= 1
                if joined:
                    valid_action = True
            elif login.lower() == "exit":
                valid_action = True

        if joined:
            user = joined[0]
            token = joined[1]
        else:
            print("Unsuccesfull login")
            client_sock.close()
            return
        
        stop_event = threading.Event()
        heartbeat_thread = threading.Thread(target=heartbeat, args=(client_sock, stop_event, token), daemon=True)
        heartbeat_thread.start()
        stop_event_chat = threading.Event()
        chat_thread = threading.Thread(target=get_incoming_messages, args=(client_sock, stop_event_chat), daemon=True)
        config["active_heartbeat"] = True
        chatting = False
    
        while True:
            status = status_check(client_sock, token)
            if status == False or config["active_heartbeat"] == False:
                client_sock.close()
                stop_event.set()
                heartbeat_thread.join()  # Wait for the thread to finish
                print(f"Disconnected client {user}, lost connection to server\n")
                break

            ask = input("Cmd: ")
            if ask == "exit":
                client_sock.close()
                stop_event.set()
                heartbeat_thread.join()  # Wait for the thread to finish
                print(f"Goodbye {user}")
                break
            if ask == "chat" and chatting == False:
                chat_thread.start()
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
                msg_content.append(input("Input: "))

            msg = gen_message(ask, msg_content, "main", token)
            send_to_server(client_sock, msg)
            got_response = recieve_from_server(client_sock)
            if got_response:
                print("Server response:", receieve_queue["main"].Pop())
                
            time.sleep(0.02)
      
        #client_sock.close()
        #print(f"Disconnected client {user}\n")
    
def main():
    client()

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
        