from loads import *
from database_manager import *
from server_utils import *

def friend_request():
    pass

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

def show_online_users(msg, token):
    """Returns a list of all online users
       return: {"data": users, "signal": signal}"""
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

def show_room_users(msg, token):
    payload = get_user_profile(token)
    signal = msg
    if payload:
        users = {"data": []}
        return {"data": users, "signal": signal} 
    else:
        return "show_room_users->invalid token"

def update_users_count(amount = 1):
    """Updates the user count in the config file"""
    config["user_count"] += amount
    with open(config_path, "w") as file:
        json.dump(config, file, indent=4)  

def _join_room(recieving_username, token): #depricated
    """Adds a user to a room or creates a new room if it doesn't exist"""
    try:
        payload = get_user_profile(token)
        recieving_username = recieving_username[0]
        if payload:
            sending_username = payload["name"]
            print(f"User {sending_username} is attempting to join a room with {recieving_username}")
            recieving_user = get_user(recieving_username)
            potential_key = str(sorted([sending_username, recieving_username]))

            #Check for existing room invites
            invites = get_room_invite(sending_username)
            if potential_key in invites:
                room_id = invites[potential_key] 
                success = join_2user_room(sending_username, room_id)
                if success:
                    del invites[potential_key] #remove the invite after joining
                    #Cleanup old room if exists
                    if len(payload["rooms_joined"]) > 0:
                        old_key = payload["rooms_joined"][-1][0]
                        old_id = payload["rooms_joined"][-1][1]
                        delete_2user_room(None, None, old_id, old_key)  
                        print("Deleted room {old_key} with ID {old_id}")

                    print(f"User {sending_username} joined room with {recieving_username} with id {room_id}")
                    payload["subscribed_room"] = room_id
                    payload["rooms_joined"].append([potential_key, room_id])
                    return "join_room->success"

            #If no invite create a room and invite the user
            if recieving_user:
                status, id = create_2user_room(sending_username, recieving_username)
                if status == "created":
                    #Cleanup old room if exists
                    if len(payload["rooms_joined"]) > 0:
                        old_key = payload["rooms_joined"][-1][0]
                        old_id = payload["rooms_joined"][-1][1]
                        delete_2user_room(None, None, old_id, old_key)  
                        print("Deleted room {old_key} with ID {old_id}")

                    #create new room and send invite
                    payload["subscribed_room"] = id
                    invites = get_room_invite(recieving_username)
                    invites[potential_key] = id
                    payload["rooms_joined"].append([potential_key, id])
                    print(f"Room created between {sending_username} and {recieving_username} with id {id}")
                    return "join_room->room created->invite sent"
                
                elif status == "found":
                    print(f"Room already exists between {sending_username} and {recieving_username} with id {id}")
                    return "join_room->room_exists"

        else:
            return "join_room->invalid token"
        
    except Exception as e:
        print(f"join_room->Error: {e}")
        return "join_room->error"

def join_room(receiving_username, token):
    """Join or create a persistent DM room between two users."""

    try:
        payload = get_user_profile(token)

        if not payload:
            return "join_room->invalid token"

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

def leave_room(msg, token):
    """Leave the current room without deleting it."""

    try:
        payload = get_user_profile(token)

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

def ping(msg, token=None): #updates users heartbeat time to maintain status health
    """Updates the heartbeat time of the user to maintain status health"""
    """Returns "pong" if the user is online and the heartbeat time is updated"""
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