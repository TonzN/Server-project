from loads import *
from database_manager import *
from server_utils import *

async def message_group(loop, data, tag, token):
    try:
        profile = get_user_profile(token)
        if profile:
            group = data[0]
            msg = data[1]
            if get_group(group):
                if group == "global":
                    online_users = get_all_online_users()
                    for user in online_users:
                        if user != profile["name"]:
                            client_socket = get_user(user)
                            response = json.dumps({"data": [{"user": "[global]"+profile["name"], "message": msg, "signal": "chat"}, "chat", ],  "signals": "chat"}) + "\n"
                            await client_socket.send(response.encode()) #to send other users messages you need their socket
                    return f"Sent message to {group}"
            else:
                return "invalid group"
        else:
            return "invalid token"
    
    except asyncio.TimeoutError:
        print("Socket timout, could not send or recieve in time")
        return "Did not send message"
    
    except Exception as e:
        print(f"could not recieve or send back to group or error with provided data {e}")
        return "Did not send message"

async def message_user(loop, data, tag, token):
    try:
        profile = get_user_profile(token)
        if profile:
            username = data[0]
            msg = data[1]
            user = get_user(username)
            if user:
                client_socket = user
            else:
                return f"{user} is not online"
            
            response = json.dumps({"data": [{"user": profile["name"], "message": msg, "signal": "chat"}, "chat"]}) + "\n"
            await client_socket.send(response.encode()) #to send other users messages you need their socket
            logg_message(profile, username, msg)
            return f"Sent message to {user}"
        else:
            return "invalid token"
    
    except asyncio.TimeoutError:
        print("Socket timout, could not send or recieve in time")
        return "Did not send message"
    
    except Exception as e:
        print(f"could not recieve or send back to client or error with provided data {e}")
        return "Did nto send message"


def remove_profile(key):
    pass

def logg_message(profile, target_user, msg):
    try:
        if profile and target_user and msg:
            log = {"user": profile["name"], "target": target_user, "message": msg}
    except Exception as e:
        print(f"Could not log message {e}")
        return False

def pull_chat_history(user):
    pass

def pull_group_chat_history(group):
    pass