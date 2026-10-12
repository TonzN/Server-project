from auth_context import authenticated, UserContext
from loads import *
from database_manager import *
from server_utils import *
import group_manager as gm
from group_manager import get_group
from datetime import datetime

#----------------requests-----------------
"""Expected incoming data format:
    [recieving, message, message_type, channel_id/room_id= None]
    message_type can be "dm", "group", or "room" (multi user chat)
    """

@authenticated(denied="message_user->invalid token")
async def message_user(data, token, *, auth_user: UserContext):
    """Send a message to a user.
       \nThe data should be in the format: [username, message]
       \n Only sends to users in the same room, if user is not it will still store the message in the database for later retrieval"""
    """Returns a message indicating whether the message was sent successfully or not."""
    try:
        profile = auth_user.session
        if profile:
            sending_username = profile["name"]
            room_id = profile["subscribed_room"]
            recieving_username = data[0]
            msg = data[1]
            recieving_user = get_user(recieving_username)
            
            if recieving_user:
                room = gm.automated_room_asignment(profile, sending_username, recieving_username, "dm", room_id)
                print("Message sent in room with: ", room)
                recieving_client_socket = None
                if isinstance(room, list):  
                    for user in room:
                        if user == recieving_username:
                            recieving_client_socket = get_user(recieving_username)
                            break
                else:
                    return f"Was not able to find a room for {sending_username} and {recieving_username}"
            else:
                return f"{recieving_username} is not online"
            
            if recieving_client_socket:
                response = json.dumps({"data": [{"user": sending_username, "message": msg, "signal": "chat"}, "chat"]}) + "\n"
            else:
                return f"{recieving_username} is not in the room"
            
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
    
#legacy code
@authenticated(denied="message_group->invalid token")
async def message_group(data, token, *, auth_user: UserContext):
    try:
        profile = auth_user.session
        if profile:
            group = data[0]
            msg = data[1]
            room_id = profile["subscribed_room"]
            group = get_group(group)
            if group and room_id == group.name:
                online_users = group.users
                for user in online_users:
                    if user != profile["name"]:
                        client_socket = get_user(user)
                        response = json.dumps({"data": [{"user": "[global]"+profile["name"], "message": msg, "signal": "chat"}, "chat", ],  "signals": "chat"}) + "\n"
                        await client_socket.send(response.encode()) #to send other users messages you need their socket
                print(f"message_group->Sent message from {user} in group {group.name}")
                await group_logg_message(profile, group.name, msg)
                return f"Sent message to {group.name}"
            else:
                return f"message_group->invalid group | {room_id} or {group.name if group else 'None'}"
        else:
            return "message_group->invalid token"
    
    except asyncio.TimeoutError:
        print("message_group->Socket timout, could not send or recieve in time")
        return "message_group->Did not send message"
    
    except Exception as e:
        print(f"message_group->could not recieve or send back to group or error with provided data {e}")
        return "message_group->Did not send message"
    
#---------------------mix----------------------------
@authenticated(denied="pull_all_chat_history->invalid token")
async def pull_all_chat_history(data, token, *, auth_user: UserContext):
    """Pull all chat history from the database.
       \nThe data should be in the format: [group]"""
    """Returns a message indicating whether the message was sent successfully or not."""

    try:
        profile = auth_user.session
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
    """Convert a record to a dictionary and format the timestamp."""
    r = dict(record)
    if isinstance(r.get("timestamp"), datetime):
        r["timestamp"] = r["timestamp"].isoformat()  # or str(r["timestamp"])
    return r

@authenticated(denied="pull_user_chat_history_to_user->invalid token")
async def pull_user_chat_history_to_user(data, token, *, auth_user: UserContext):
    """Pull chat history from a user to another user.
       \nThe data should be in the format: [username]"""
    """Returns a message indicating whether the message was sent successfully or not."""

    try:
        profile = auth_user.session
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