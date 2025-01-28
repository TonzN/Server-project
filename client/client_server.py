import socket
import asyncio
import json
import time
import threading
import datastructures as ds

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 12345  # The port used by the server

config_path = "client/client_config.json" #incase path changes
run_terminal = True
HEARTBEAT_INTERVAL = 5
short_lived_client = True

server_response_log = []
receieve_queue = { #tag associated with where message has associated function
    "heartbeat": ds.Queue(),
    "join_protocol": ds.Queue(),
    "main": ds.Queue()
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

def recieve_from_server(client_sock, expected_tag=None):
    try:
        data = client_sock.recv(1024)
    except Exception as e:
        add_to_response_log(None)
        print(f"Could not recieve from server: {e}\n")
        return None
    except socket.timeout():
        add_to_response_log(None)
        print("Timed out trying to receieve from server")
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
            print(f"invalid tag {tag}")
            return False
        
        return True

def new_user_protocol():
    pass

def gen_message(action="", data="", tag=""):
    return {"action": action, "data":data, "tag": tag}

def add_to_response_log(response):
    log_len = len(server_response_log)
    if log_len < 5:
        server_response_log.append(response)
    else:
        server_response_log.pop(0)
        server_response_log.append(response)

def client_joined(client_sock, r_queue):
    user = input("Username: ")
    message = gen_message("veus", user, "join_protocol")
    send_to_server(client_sock, message)
    got_response = recieve_from_server(client_sock, ["join_protocol", 0])
    
    if got_response:
        response = receieve_queue["join_protocol"].Pop()
        if int(response) == 1:
            message = {"user": user, "socket": str(client_sock)}
            msg = gen_message("set_user", message , "join_protocol")
            send_to_server(client_sock, msg)
            got_response = recieve_from_server(client_sock, ["join_protocol", 0])
            if got_response:
                set_user = receieve_queue["join_protocol"].Pop()
                if set_user:
                    print(f"Welcome back {user}")
                else:
                    print("Could not set up server profile, profile may already be setup")
                    return False

            else:
                print("Did not get set user or server disconnected")
                return False
        else:
            print(f"User does not exist. Want to create a user?")
            user_rsp = input("y/n? \nAnswer: ")
            if user_rsp.lower() == "y":
                new_user_protocol()
            else:
                print("Make a user to use this server.")
    else:
        print("Did not receieve from server or some unexpected error happebned")
        False

    return user

def status_check(client_socket, force_ping = False):
    for response in server_response_log:
        if response == "disconnect":
            print("Warning: server disconnected client")
            return False
        
        if response == None or force_ping == True: #ping server
            for i in range(3):
                msg = gen_message("ping", "ping")
                connection = send_to_server(client_socket, msg, True)
                if connection:
                    if recieve_from_server(client_socket) == "pong":
                        return True
                
                time.sleep(0.05)
            print("Could not ping server, no connection to server")
            return False
    
    return True
    #ping

def heartbeat(client_socket, stop):
    while not stop.is_set():
        msg = gen_message("ping", "ping", "heartbeat")
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
        
        stop_event = threading.Event()
        heartbeat_thread = threading.Thread(target=heartbeat, args=(client_sock, stop_event), daemon=True)
        heartbeat_thread.start()
        config["active_heartbeat"] = True
        response_queue = ds.Queue()
        user = client_joined(client_sock, response_queue)
        while True:
            status = status_check(client_sock)
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

            if ask == "ping":
                msg_content = "ping"
            else:
                msg_content = input("Message to server: ")

            msg = gen_message(ask, msg_content, "main")
            send_to_server(client_sock, msg)
            got_response = recieve_from_server(client_sock)
            if got_response:
                print("Server response:", receieve_queue["main"].Pop())
                
            time.sleep(0.02)
      
        #client_sock.close()
        #print(f"Disconnected client {user}\n")
    
def main():
    client()

while run_terminal:
    time.sleep(0.1)
    server_response_log = []    

    cmd = input("command: ")
    if cmd == "close":
        run_terminal = False

    if cmd == "connect":
        main()
        