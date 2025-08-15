from loads import *
from database_manager import *
from server_utils import *
import group_manager as gm
from datetime import datetime

def message_manage(func):
    def wrapp(token):
        """Get a user profile by their token."""
        return get_user_profile(token)

def parse_data_payload(func):
    pass

def logging(func):
    pass

def error_catching(func):
    pass

def server_security(func):
    """Check if the server is secure.
    Rate limiting, IP blocking, etc."""

    pass

#----------------requests-----------------
"""Expected incoming data format:
    [recieving, message, message_type, channel_id/room_id= None]
    message_type can be "dm", "group", or "room" (multi user chat)
    """

async def message_user(data, token):
    """Send a message to a user.
       \nThe data should be in the format: [username, message]
       \n Only sends to users in the same room, if user is not it will still store the message in the database for later retrieval"""
    """Returns a message indicating whether the message was sent successfully or not."""
    try:
        profile = get_user_profile(token)
        if profile:
            sending_username = profile["name"]
            room_id = profile["subscribed_room"]
            recieving_username = data[0]
            msg = data[1]
            recieving_user = get_user(recieving_username)
            
            if recieving_user:
                room = gm.automated_room_asignment(profile, sending_username, recieving_username, "dm", room_id)
                recieving_client_socket = None
                if room:
                    for user in room:
                        if user == recieving_username:
                            recieving_client_socket = get_user(recieving_username)
                            break
                else:
                    return f"Was not able to find a room for {sending_username} and {recieving_username}"
            else:
                return f"{recieving_username} is not online"
            
          
            response = json.dumps({"data": [{"user": sending_username, "message": msg, "signal": "chat"}, "chat"]}) + "\n"
            await recieving_client_socket.send(response.encode()) #to send other users messages you need their socket

            try:
               await logg_message(profile, recieving_username, msg) # log the message even if the user is not online or in the same room
            except Exception as e:
                print(f"message_user->could not log message {e}")
                return "message_user->Did not log message"

            return f"Sent message to {recieving_username}"
        else:
            return "message_user->invalid token"
    
    except asyncio.TimeoutError:
        print("Socket timout, could not send or recieve in time")
        return "message_user->Did not send message"
    
    except Exception as e:
        print(f"message_user->could not recieve or send back to client or error with provided data {e}")
        return "message_user->Did not send message"
    
async def new_message_group(data, token):
    """Send a message to a group.
       \nThe data should be in the format: [group, message]"""
    try:
        profile = get_user_profile(token)
        if profile:
            group = data[0]
            msg = data[1]
            room = None
            subscribed_room = profile["subscribed_room"]
          #  room = get_room(subscribed_room)
            if get_group(group):
                if group == "global" and room == "global":
                    for subscribed_user in room:
                        if subscribed_user != profile["name"]:
                            client_socket = get_user(subscribed_user)
                            response = json.dumps({"data": [{"user": profile["name"], "message": msg, "signal": "chat"}, "chat", ],  "signals": "chat"}) + "\n"
                            await client_socket.send(response.encode()) #to send other users messages you need their socket
                    try:
                        await group_logg_message(profile, group, msg)
                    except Exception as e:
                        print(f"message_group->could not log message {e}")
                        return "message_group->Did not log message"
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

#legacy code
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
                            await logg_message(profile, user, msg)
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
    

def _auto_group(profile, data):
    """Automatically add a user to a group when they join a room.
    if the group does not exist, create it.
    Returns group or channel id"""
    sending_username = profile["name"]
    recieving_username = data[0]


#legacy code
async def old_message_user(data, token):
    """Send a message to a user.
       \nThe data should be in the format: [username, message]
       \n Only sends to users in the same room, if user is not it will still store the message in the database for later retrieval"""
    """Returns a message indicating whether the message was sent successfully or not."""
    try:
        profile = get_user_profile(token)
        if profile:
            sending_username = profile["name"]
            recieving_username = data[0]
            msg = data[1]

            recieving_user = get_user(recieving_username)
            
            if recieving_user:
                recieving_client_socket = recieving_user
            else:
                return f"{recieving_username} is not online"
            
          
            response = json.dumps({"data": [{"user": sending_username, "message": msg, "signal": "chat"}, "chat"]}) + "\n"
            await recieving_client_socket.send(response.encode()) #to send other users messages you need their socket

            try:
               await logg_message(profile, recieving_username, msg) # log the message even if the user is not online or in the same room
            except Exception as e:
                print(f"message_user->could not log message {e}")
                return "message_user->Did not log message"

            return f"Sent message to {recieving_username}"
        else:
            return "message_user->invalid token"
    
    except asyncio.TimeoutError:
        print("Socket timout, could not send or recieve in time")
        return "message_user->Did not send message"
    
    except Exception as e:
        print(f"message_user->could not recieve or send back to client or error with provided data {e}")
        return "message_user->Did not send message"


#---------------------mix----------------------------
async def pull_all_chat_history(data, token):
    """Pull all chat history from the database.
       \nThe data should be in the format: [group]"""
    """Returns a message indicating whether the message was sent successfully or not."""

    try:
        profile = get_user_profile(token)
        if profile:
            group = "global"
            chat_history = await db_get_all_messages_from_group(group)
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
    """Convert a record to a dictionary and format the timestamp."""
    r = dict(record)
    if isinstance(r.get("timestamp"), datetime):
        r["timestamp"] = r["timestamp"].isoformat()  # or str(r["timestamp"])
    return r

async def pull_user_chat_history_to_user(data, token):
    """Pull chat history from a user to another user.
       \nThe data should be in the format: [username]"""
    """Returns a message indicating whether the message was sent successfully or not."""

    try:
        profile = get_user_profile(token)
        sender = profile["name"]
        if profile:
            username = data[0]
            user = await db_find_user_profile(username)
            if not user:
                return f"{user} is not online"
       
            chat_history = await db_get_messages_from_user_to(sender, username)

            return {"user": username, "message": [serialize_record(record) for record in chat_history], "signal": "chat"}
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
    """Log a message to the database.
       \nThe data should be in the format: [username, message]"""
    try:
        if profile and target_user and msg:
            #format: sender, receiver, message
            log = [profile["name"], target_user, msg]
            await db_add_message(log)
    except Exception as e:
        print(f"Could not log message {e}")
        return False
    
async def group_logg_message(profile, group, msg):
    """Log a message to the database.
       \nThe data should be in the format: [group, message]"""
    try:
        if profile and group and msg:
            #format: sender, receiver, message
            log = [profile["name"], group, msg]
            await db_add_message(log)
    except Exception as e:
        print(f"Could not log message {e}")
        return False