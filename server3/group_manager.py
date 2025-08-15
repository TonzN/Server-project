import database_manager as db

class GroupChat:
    def __init__(self, name):
        self.name = name

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
            if reciever == sender: #if the reciever is the same as the sender, return None
                print("Error: automated_room_asgn. Reciever is the same as sender. \n Sender: {}, Reciever: {}".format(sender, reciever))
                return None

            room_id = db.get_2user_room_id(sender, reciever)

            if not room_id:
                print("no room found for sender and reciever. Creating a new room.")
                room_id = db.create_2user_room(sender, reciever)

            if room_id == id:
                return db.get_2user_room(room_id) #no room designation change needed. 
            else: #switch room
                db.switch2_user_room(senderprofile, room_id, id, sender, reciever)
        
            #if room still not found, return None
            if not room_id: #to make sure internal errors dont cause issues for unexepected room errors.
                print("Error: automated_room_asgn. Could not create or find a 2 user room. \n Sender: {}, Reciever: {}".format(sender, reciever))
                return None

            return db.get_2user_room(room_id)
    
    except Exception as e:
        print(f"automated_room_asignment->Error: {e}")
        return None
    