from auth_context import authenticated, UserContext
from loads import *
from database_manager import *
from server_utils import *

def kill_server(msg, token):
    """This function doesnt exist :)"""
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

@authenticated(denied="show_online_users->invalid token")
def show_online_users(msg, token, *, auth_user: UserContext):
    """Returns a list of all online users
       return: {"data": users, "signal": signal}"""
    payload = auth_user.session
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
    """Updates the user count in the config file"""
    config["user_count"] += amount
    with open(config_path, "w") as file:
        json.dump(config, file, indent=4)  

@authenticated(denied="join_group_chat->invalid token")
def join_group_chat(group_name, token, *, auth_user: UserContext):
    """Join a group chat by name."""
    try:
        payload = auth_user.session
        if not payload:
            return "join_group_chat->invalid token"

        current_room = payload.get("subscribed_room")
        username = payload["name"]
        group_chat = get_group(group_name[0])
        
        if current_room and current_room != group_chat.name: # If the user is already in a room and it's not the group chat they want to join, leave the current room first
            leave_room(payload, token)  # Leave current room before joining a new one incase the user is already in a room
            leave_group_chat(current_room, token)  # Leave current group chat if the user is already in one
            
        if not group_chat:
            return f"join_group_chat->group chat not found {group_name}"

        if not group_chat.add_user({"name": username}):
            payload["subscribed_room"] = group_chat.name  #incase user leaves and rejoins the group chat, update the subscribed room to the group chat name
            return "join_group_chat->user already in group chat"

        payload["subscribed_room"] = group_chat.name  # Update the user's subscribed room to the group chat name
        print(f"{username} joined group chat {group_name}")
        return "join_group_chat->success"

    except Exception as e:
        print(f"join_group_chat->Error: {e}")
        return "join_group_chat->error"

@authenticated(denied="join_room->invalid token")
def join_room(receiving_username, token, *, auth_user: UserContext):
    """Join or create a persistent DM room between two users."""

    try:
        payload = auth_user.session

        if not payload:
            return "join_room->invalid token"

        print(leave_group_chat(payload.get("subscribed_room"), token))  # Leave current group chat if the user is already in one
        # Request currently sends username as a list
        receiving_username = receiving_username[0]

        sending_username = payload["name"]

        if sending_username == receiving_username:
            return "join_room->cannot chat with yourself"

        # Make sure receiving user exists
        if not get_user(receiving_username):
            return "join_room->user not found"

        # Find existing room
        room_id = get_2user_room_id(
            sending_username,
            receiving_username
        )

        # No room exists -> create it
        if room_id is None:

            result = create_2user_room(
                sending_username,
                receiving_username
            )

            if not result:
                return "join_room->failed to create room"

            status, room_id = result

        # Switch from current room to the DM room
        if not switch2_user_room(payload, room_id):
            return "join_room->failed to switch room"

        print(
            f"{sending_username} joined DM with "
            f"{receiving_username} "
            f"(room {room_id})"
        )

        return {
            "status": "success",
            "room_id": room_id
        }

    except Exception as e:
        print(f"join_room->Error: {e}")
        return "join_room->error"

@authenticated(denied="leave_room->invalid token")
def leave_room(msg, token, *, auth_user: UserContext):
    """Leave the current room without deleting it."""

    try:
        payload = auth_user.session

        if not payload:
            return "leave_room->invalid token"

        room_id = payload.get("subscribed_room")
        
        if not room_id:
            return "leave_room->no room joined"

        username = payload["name"]

        # Remove user from active users
        if not leave_2user_room(username, room_id):
            return "leave_room->failed"

            
        # User is no longer subscribed to this room
        payload["subscribed_room"] = None

        print(
            f"{username} left room {room_id}"
        )

        return "leave_room->success"

    except Exception as e:
        print(f"leave_room->Error: {e}")
        return "leave_room->error"

@authenticated(denied="leave_group_chat->invalid token")
def leave_group_chat(group_name, token, *, auth_user: UserContext):
    """Leave a group chat by name."""
    try:
        payload = auth_user.session
        if not payload:
            return "leave_group_chat->invalid token"

        username = payload["name"]
        group_chat = get_group(group_name)

        if not group_chat:
            return "leave_group_chat->group chat not found"

        user = group_chat.find_user(username)
        if not user:
            return "leave_group_chat->user not in group chat"

        if not group_chat.remove_user(username):
            return "leave_group_chat->user not in group chat"

        payload["subscribed_room"] = None  # Update the user's subscribed room to None
        print(f"{username} left group chat {group_name}")
        return "leave_group_chat->success"

    except Exception as e:
        print(f"leave_group_chat->Error: {e}")
        return "leave_group_chat->error"
    
@authenticated(denied=False)
def ping(msg, token=None, *, auth_user: UserContext): #updates users heartbeat time to maintain status health
    """Updates the heartbeat time of the user to maintain status health"""
    """Returns "pong" if the user is online and the heartbeat time is updated"""
    if token:
        try:
            user = auth_user.session
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