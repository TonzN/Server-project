import json

config_path = "server/config.json" #incase path changes
users_path = "server/users.json"

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

try: #attempt fetching users
    with open(users_path, 'r') as file:
        users = json.load(file)
        print("JSON file loaded successfully!")
except FileNotFoundError:
    print(f"Error: The file '{users_path}' does not exist.")
except json.JSONDecodeError:
    print(f"Error: The file '{users_path}' contains invalid JSON.")
except PermissionError:
    print(f"Error: Permission denied while accessing '{users_path}'.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
