import json
import socket
import asyncio
import json
import time
import sys
import os
import random

def get_config_path():
    if getattr(sys, 'frozen', False):
        # Running in a bundled executable
        base_path = sys._MEIPASS
    else:
        # Running in a normal Python environment
        base_path = os.path.dirname(__file__)

    return os.path.join(base_path, 'client_config.json')

config_path = get_config_path() #incase path changes

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
