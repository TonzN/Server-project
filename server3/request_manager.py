from loads import *
from database_manager import *
from server_utils import *

def friend_request():
    pass

def kill_server(msg, token):
    user = get_user_profile(token)
    if user:
        username = user["name"]
        id = user["id"]
        userfile = get_user_json_profile(username)
        if userfile["permission_level"] == "admin":
            print(f"User {username}#{id} killed the server!!")
            print(msg)
            os._exit(0)
        else:
            return "kill_server->Not high enough access level"
    return "kill_server->Unverfied token"

def show_online_users(msg, token):
    payload = get_user_profile(token)
    signal = msg
    if payload:
        users = {"data": []}
        online_users = get_all_online_users()
        for user in online_users:
            users["data"].append(user)
        return {"data": users, "signal": signal}
    else:
        return "show_online_users->invalid token"
    
def update_users_count(amount = 1):
    config["user_count"] += amount
    with open(config_path, "w") as file:
        json.dump(config, file, indent=4)  

def ping(msg, token=None): #updates users heartbeat time to maintain status health
    if token:
        try:
            user = get_user_profile(token)
            if user:
                if msg == "ping":
                    print("ping")
                user["heartbeat"] = time.time()
                return "pong"
            #else:
              #  print(f"missing token | user: {user}\n")
        except Exception as e:
            print(f"Error pinging user: {e}\nuser: {user}")
            return False