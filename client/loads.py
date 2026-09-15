import json
import os
import sys
import socket
import asyncio
import time

APP_NAME = "SuperApp"


def get_bundled_config_path():
    """
    Returns the path to the default config bundled with the application.
    """
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
        return os.path.join(base_path, "client", "client_config.json")

    return os.path.join(os.path.dirname(__file__), "client_config.json")


def get_user_config_path():
    """
    Returns a persistent config path for the current Windows user.
    Example:
    C:\\Users\\Toni\\AppData\\Local\\SuperApp\\client_config.json
    """
    local_appdata = os.environ.get("LOCALAPPDATA")

    if not local_appdata:
        # Fallback, mainly useful outside Windows
        local_appdata = os.path.expanduser("~")

    config_dir = os.path.join(local_appdata, APP_NAME)
    os.makedirs(config_dir, exist_ok=True)

    return os.path.join(config_dir, "client_config.json")


bundled_config_path = get_bundled_config_path()
config_path = get_user_config_path()

try:
    # If user config doesn't exist yet, create it from bundled defaults
    if not os.path.exists(config_path):
        with open(bundled_config_path, "r", encoding="utf-8") as file:
            default_config = json.load(file)

        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(default_config, file, indent=4)

    # Load persistent user config
    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

except FileNotFoundError as e:
    print(f"Config file not found: {e}")

except json.JSONDecodeError as e:
    print(f"Invalid JSON in config file: {e}")

except PermissionError as e:
    print(f"Permission denied while accessing config: {e}")

except Exception as e:
    print(f"Unexpected config error: {e}")