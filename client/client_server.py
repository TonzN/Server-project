import socket
import asyncio
import json
import time

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 12345  # The port used by the server

config_path = "config.json" #incase path changes
users_path = "users.json" #incase path changes
run_terminal = True
short_lived_client = True

server_response_log = []

def send_to_server(client_sock, msg):
    if type(msg) is dict:
        try:
            client_sock.sendall(json.dumps(msg).encode())
            return True
        except Exception as e:
            print(f"Could not send message to server {e}\n")
    else:
        print("Invalid message format, please send as dictionary")

def recieve_from_server(client_sock):
    try:
        data = client_sock.recv(1024)
    except Exception as e:
        print(f"Could not recieve from server: {e}\n")
        return None
    return json.loads(data.decode())["data"][0]

def new_user_protocol():
    pass

def gen_message(action="", data=""):
    return {"action": action, "data":data}

def add_to_response_log(response):
    log_len = len(server_response_log)
    if log_len < 5:
        server_response_log.append(response)
    else:
        server_response_log.pop(0)
        server_response_log.append(response)

def client_joined(client_sock):
    user = input("Username: ")
    message = gen_message("veus", user)
    send_to_server(client_sock, message)
    response = recieve_from_server(client_sock)
    add_to_response_log(response)
  
    if response:
        if int(response) == 1:
            print(f"Welcome back {user}")
        else:
            user = "nan"
            print(f"User does not exist. Want to create a user?")
            user_rsp = input("y/n? \nAnswer: ")
            if user_rsp.lower() == "y":
                new_user_protocol()
            else:
                print("Make a user to use this server.")
    else:
        user = "nan"

    return user

def status_check(client_socket):
    for response in server_response_log:
        print(response)
        if response == "disconnect":
            print("Warning: server disconnected client")
            return False
        
        if response: #ping server
            for i in range(3):
                msg = gen_message("ping", "ping")
                connection = send_to_server(client_socket, msg)
                if connection:
                    if recieve_from_server(client_socket) == "pong":
                        return True
                
                time.sleep(0.05)
            print("Could not ping server, no connection to server")
            return False
    
    return True
    #ping

def client(): #activates a client
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock:
        try:
            client_sock.connect((HOST, PORT))
            print(f"Client connected.\n")
        except Exception as e:
            print(f"Client did not connect: {e}\n")
            return
    
        user = client_joined(client_sock)
        status = status_check(client_sock)
        if status == False:
            client_sock.close()
            print(f"Disconnected client {user}, lost connection to server\n")
      
        #client_sock.close()
        #print(f"Disconnected client {user}\n")
    
def main():
    client()

while run_terminal:
    time.sleep(0.1)
    main()

    cmd = input("command: ")
    if cmd == "close":
        run_terminal = False
        