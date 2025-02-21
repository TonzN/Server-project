import json
import socket
import asyncio
import json
import time
import os
import threading

config_path = "client/client_config.json" #incase path changes

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
