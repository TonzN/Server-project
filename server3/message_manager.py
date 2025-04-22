from loads import *
from database_manager import *
from server_utils import *
from datetime import datetime

#----------------requests-----------------
async def message_group(data, token):
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
                            await group_logg_message(profile, group, msg)
                    return f"Sent message to {group}"
            else:
                return "message_group->invalid group"
        else:
            return "message_group->invalid token"
    
    except asyncio.TimeoutError:
        print("message_group->Socket timout, could not send or recieve in time")
        return "message_group->Did not send message"
    
    except Exception as e:
        print(f"message_group->could not recieve or send back to group or error with provided data {e}")
        return "message_group->Did not send message"

async def message_user(data, token):
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
            await logg_message(profile, username, msg)
            return f"Sent message to {user}"
        else:
            return "message_user->invalid token"
    
    except asyncio.TimeoutError:
        print("Socket timout, could not send or recieve in time")
        return "message_user->Did not send message"
    
    except Exception as e:
        print(f"message_user->could not recieve or send back to client or error with provided data {e}")
        return "message_user->Did not send message"

async def pull_all_chat_history(data, token):
    try:
        profile = get_user_profile(token)
        if profile:
            group = "global"
            chat_history = await db_get_all_messages_from(group)
            return {"user": profile["name"], "message": [serialize_record(record) for record in chat_history], "signal": "chat"}
        else:
            return "pull_all_chat_history->invalid token"
        
    except asyncio.TimeoutError:    
        print("Socket timout, could not send or recieve in time")
        return "pull_all_chat_history->Did not send request"
    except Exception as e:  
        print(f"pull_all_chat_history->could not recieve or send back to client or error with provided data {e}")
        return "pull_all_chat_history->Did not send request"

def serialize_record(record):
    r = dict(record)
    if isinstance(r.get("timestamp"), datetime):
        r["timestamp"] = r["timestamp"].isoformat()  # or str(r["timestamp"])
    return r

async def pull_user_chat_history_to_user(data, token):
    try:
        profile = get_user_profile(token)
        sender = profile["name"]
        if profile:
            username = data[0]
            user = await db_find_user_profile(username)
            if not user:
                return f"{user} is not online"
            
            if data[1] == "sent":
                chat_history = await db_get_messages_from_user_to(sender, username)
            elif data[1] == "recieved":
                chat_history2 = await db_get_messages_from_user_to(username, sender)


            return {"user": username, "message": zip([serialize_record(record) for record in chat_history], [serialize_record(record) for record in chat_history2]), "signal": "chat"}
        else:
            return "pull_user_chat_history_to_user->invalid token"
    
    except asyncio.TimeoutError:
        print("Socket timout, could not send or recieve in time")
        return "pull_user_chat_history_to_user->Did not send request"
    
    except Exception as e:
        print(f"pull_user_chat_history_to_user->could not recieve or send back to client or error with provided data {e}")
        return "pull_user_chat_history_to_user->Did not send request"
    
#----------logic-------------------
async def logg_message(profile, target_user, msg):
    try:
        if profile and target_user and msg:
            #format: sender, receiver, message
            log = [profile["name"], target_user, msg]
            await db_add_message(log)
    except Exception as e:
        print(f"Could not log message {e}")
        return False
    
async def group_logg_message(profile, group, msg):
    try:
        if profile and group and msg:
            #format: sender, receiver, message
            log = [profile["name"], group, msg]
            await db_add_message(log)
    except Exception as e:
        print(f"Could not log message {e}")
        return False