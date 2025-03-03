import json
import socket
import asyncio
import json
import time
import os
import threading
import random

config_path = "client/client_config.json" #incase path changes

try: #attempt fetching configs
    with open(config_path, 'r') as file:
        temp = json.load(file)

    config_path = f"client_config#{random.randint(0,100000)}.json"
    with open(config_path, "w") as file:
        json.dump(temp, file, indent=4)
    with open(config_path, "r") as file:
        config = json.load(file)
    
except FileNotFoundError:
    print(f"Error: The file '{config_path}' does not exist.")
except json.JSONDecodeError:
    print(f"Error: The file '{config_path}' contains invalid JSON.")
except PermissionError:
    print(f"Error: Permission denied while accessing '{config_path}'.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
