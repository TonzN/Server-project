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
    
def update_users_count(amount = 1):
    """Updates the user count in the config file"""
    config["user_count"] += amount
    with open(config_path, "w") as file:
        json.dump(config, file, indent=4)  

def join_room(recieving_username, token):
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
                    payload["subscribed_room"] = room_id
                    return "join_room->success"

            #If no invite create a room and invite the user
            if recieving_user:
                status, id = create_2user_room(sending_username, recieving_username)
                if status == "created":
                    payload["subscribed_room"] = id
                    invites = get_room_invite(recieving_username)
                    invites[potential_key] = id
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