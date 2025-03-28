import json
import time
import sys

chat_path = sys.argv[1] if len(sys.argv) > 1 else None

if chat_path:
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

    while True:
        time.sleep(0.2)
        with open(chat_path, 'r') as file:
            chat = json.load(file)
        if len(chat["messages"]) > 0:
            for message in chat["messages"]:
                print(message)
            chat["messages"] = []
            with open(chat_path, "w") as file:
                json.dump(chat, file, indent=4)  # Pretty print with indentation