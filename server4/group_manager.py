class GroupChat:
    def __init__(self, name):
        self.name = name
        self.users = {}
    
    def find_user(self, username):
        return self.users.get(username)

    def add_user(self, user):
        if user["name"] in self.users:
            return False  # User already exists
        self.users[user["name"]] = user
        return True
    
    def remove_user(self, username):
        user = self.find_user(username)
        if user:
            del self.users[username]
            return True
        return False

# Room/group state is owned by this module, not database_manager.
_user_room2 = {}
_rooms = {}
_room_invites = {}
_groups = {"global": GroupChat("global")}
debug_room = False

def join_2user_room(user, room_id):
    """Mark user as active in an existing room."""

    room = get_2user_room(room_id)

    if not room:
        print(
            f"join_2user_room->Error: "
            f"Room {room_id} not found"
        )
        return False

    if user not in room["users"]:
        print(
            f"join_2user_room->Error: "
            f"User {user} does not belong to room {room_id}"
        )
        return False

    room["active_users"].add(user)

    return True

def leave_2user_room(user, room_id):
    """Mark user as inactive without deleting the room."""

    try:
        room = get_2user_room(room_id)
        if room:
            room["active_users"].discard(user)
            return True
        return False
    
    except Exception as e:
        print(f"leave_2user_room->Error: {e} Room ID: {room_id}, User: {user}")
        return False
        


def get_2user_room(room_id):
    if debug_room:
        print(f"ALL ROOMS: {_rooms}") #??????????????
        for keys in _rooms:
            print("keys", keys)
            try:
                print(keys in _rooms)
            except Exception as e:                                    
                print(f"{e}")

    if room_id in _rooms:
        return _rooms[room_id]
    else:
        return None

def create_2user_room(sender, receiver):
    """Creates or returns a persistent 2-user room."""

    try:
        sorted_users = sorted([sender, receiver])
        key = str(sorted_users)

        # Room already exists
        if key in _user_room2:
            room_id = _user_room2[key]

            if room_id in _rooms:
                print(
                    f"Room already exists between "
                    f"{sender} and {receiver}"
                )

                # Sender becomes active in the existing room
                _rooms[room_id]["active_users"].add(sender)

                return "found", room_id

            # Mapping exists but room is gone
            del _user_room2[key]

        # Create new room
        from server_utils import get_random_room_id
        room_id = str(get_random_room_id())

        _user_room2[key] = room_id

        _rooms[room_id] = {
            "users": [sender, receiver],
            "active_users": {sender}
        }

        print(
            f"Created room between {sender} and {receiver} "
            f"with ID {room_id}"
        )

        return "created", room_id

    except Exception as e:
        print(f"create_2user_room->Error: {e}")
        return None
    
def switch2_user_room(senderprofile, new_room_id):

    try:

        username = senderprofile["name"]

        old_room_id = senderprofile.get("subscribed_room")

        # Leave previous active room
        if old_room_id and old_room_id != new_room_id:

            leave_2user_room(
                username,
                old_room_id
            )

        # Join new room
        if not join_2user_room(
            username,
            new_room_id
        ):
            return False

        senderprofile["subscribed_room"] = new_room_id

        return True

    except Exception as e:

        print(f"switch2_user_room->Error: {e}")

        return False

def exit_2user_room(senderprofile, sender, receiver, id=None):
    """Exit a 2 user room, this will delete the room for the users"""
    try:
        delete_2user_room(sender, receiver)
        if id:
            if id in _rooms:
                del _rooms[id]
        senderprofile["subscribed_room"] = None
        return True
    except Exception as e:
        print(f"exit_2user_room->Error: {e}")
        return False

def delete_2user_room(sender, receiver, old_room_id, key=None):
    """Deletes room for users subscribed to the same room"""
    try:
        if key == None:
            sorted_users = sorted([sender, receiver])
            key = str(sorted_users)
        if key in _user_room2:
            room_id = _user_room2[key]
            if room_id == old_room_id:
                del _user_room2[key]
                del _rooms[room_id]
            return True
        else:
            print("Room does not exist for these users")
            return False
    except Exception as e:
        print(f"delete_2user_room->Error: {e}")
        return False
    
def get_2user_room_id(sender, receiver):
    """Get 2 user room for sender and receiver
       Returns the room id if found, None if not found"""
    try:
        sorted_users = sorted([sender, receiver])
        key = str(sorted_users)
        if key in _user_room2:
            room_id = _user_room2[key]
            return room_id
        else:
            return None
    except Exception as e:
        print(f"Could not get 2 user room {e}")
        return None

def get_room_invite(user):
    """Get room invite from the room invites list
       Returns the invite of the user if found"""
    if user in _room_invites:
        return _room_invites[user]

def add_room_invite(user):
    _room_invites[user] = {}

def get_group(group):
    try:
        if group in _groups:
            return _groups[group]
        else:
            return None
    except Exception as e:
        print(f"Databasemanager-> get_group: {e}")
        return False
    
def add_group(group_name, group):
    try:
        _groups[group_name] = group
    except Exception as e:
        print(f"Could not add group {e}")
        return False

def remove_group(group_name):  
    if group_name in _groups:
        _groups[group_name] = None
        del _groups[group_name]

#quick lookup for cached data
#--------------------------------------#


""" For seemlesness internal and client sided room asignment user-user only will be done automatically internally to the server.
    For group chats or serverchats, the client will have to provide additional request information for what the client want to do."""


def automated_room_asignment(senderprofile, sender, reciever, message_type, id=None):
    """PSEUDO CODE alg steps:
    -1. sender and reciever are to be verified BEFORE this function is called!.
    0. Check if message type is dm, group, or multi user(room)
    1. Try to get a room of the sender and reciever to see if they are already in a room together
    2. If they are not in a room together, create a new room for them, and switch senders active room id
    3. If they are in a room together, return the room"""
    """ A 2 user room is not the same as a group chat, it is a direct message room."""
    
    try:
        #verify sender and reciever. 
        if message_type == "dm": #asign sender/reciever users to a 2 user room
            room_id = senderprofile["subscribed_room"]
            if room_id:
                return list(get_2user_room(room_id)["active_users"])
            else:
                print(f"automated_room_asignment->No room found for users {sender} and {reciever}")
                return 
    
    except Exception as e:
        print(f"automated_room_asignment->Error: {e}")
        return None
    