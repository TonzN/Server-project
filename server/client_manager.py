import json
import socket

config_path = "server/config.json" #incase path changes
users_path = "server/users.json" #incase path changes

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
try: #attempt fetching users
    with open(config_path, 'r') as file:
        users = json.load(file)
except FileNotFoundError:
    print(f"Error: The file '{users_path}' does not exist.")
except json.JSONDecodeError:
    print(f"Error: The file '{users_path}' contains invalid JSON.")
except PermissionError:
    print(f"Error: Permission denied while accessing '{users_path}'.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

def password_check(password):
    pass

def gen_user_id():
    creation_id = str(config["user_count"])
    id = ""
    for i in range(5-len(creation_id)):
        id += "0"
    id += creation_id
    config["user_count"]
    return id

def create_user():
    while True:
        new_username = input("New username: ")
        username = new_username.lower()
        if not username in users:
            users[username] = {}
            users[username]["username"] = new_username
            break
        
    users[username]["id"] = gen_user_id()
    users["permission_level"] = "basic"

 
