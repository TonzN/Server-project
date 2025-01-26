import socket
import asyncio
import json
import time
import sys
from pathlib import Path
import os

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 12345  # The port used by the server

config_path = "client/client_config.json" #incase path changes
run_terminal = True
short_lived_client = True

#load paths
try: #attempt fetching configs
    with open(config_path, 'r') as file:
        config = json.load(file)
        print("JSON file loaded successfully!")
except FileNotFoundError:
    print(f"Error: The file '{config_path}' does not exist.")
except json.JSONDecodeError:
    print(f"Error: The file '{config_path}' contains invalid JSON.")
except PermissionError:
    print(f"Error: Permission denied while accessing '{config_path}'.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")


def send_to_server(client_sock, msg): #attempts sending to server, must be in json format
    if type(msg) is dict:
        try:
            client_sock.sendall(json.dumps(msg).encode("utf-8"))
        except Exception as e:
            print(f"Could not send message to server {e}\n")
    else:
        print(f"Protocol doesnt allow for {type(msg)} msg must me formatted in dictionary(action: ..., data: ...)")

def recieve_from_server(client_sock): #attempts recieving
    try:
        data = client_sock.recv(1024)
    except Exception as e:
        print(f"Could not recieve from server: {e}\n")
        return
    return json.loads(data.decode())

def new_user_protocol():
    valid_username = False
    while not valid_username:
        username = input("New username: ")


def client_joined(client_sock): #checks wether the username is in the server or not
    user = str(input("Username: "))
    message = {"action": "veus", "data": user}
    send_to_server(client_sock, message )
    response = recieve_from_server(client_sock)["data"]
    if int(response) == 1:
        print(f"Welcome back {user}")
    else:
        user = "nan"
        print(f"User does not exist. Want to create a user?") #iniate new_user
        new_user = input("y/n? ")
        if new_user.lower() == "y":
            new_user_protocol()
    
    return user


def client(): #activates a client
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock:
        try:
            client_sock.connect((HOST, PORT)) #establish client connection to server
            print(f"Client connected.\n")
        except Exception as e:
            print(f"Client did not connect: {e}\n")
            return

        for i in range(10):
            user = client_joined(client_sock)
  
            
        client_sock.close()
        print(f"Disconnected client {user}\n")
    
def main():
    client()

while run_terminal:
    time.sleep(0.1)
    main()

    cmd = input("command: ")
    if cmd == "close":
        run_terminal = False
        

    
