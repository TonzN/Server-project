from loads import *
from database_manager import *
import server_utils as utils

async def verify_user(user_data):
    try:
        username = user_data["username"]
        password = user_data["password"]
        token = user_data["token"]

    except Exception as e:
        print(f"invalid data provided {e}")
        return 0
    
    try:
        userfile = await db_get_user_profile(username)
        if userfile:
            profile = utils.get_user_profile(token)
            if not profile:
                if utils.verify_password(userfile["password"], password):
                    return 1
                else:
                    return 0
            return 2
    except Exception as e:
        print(f"Error retrieving user profile: {e}")
    return 0

async def get_permission_level(msg, token):
    user = utils.get_user_profile(token)
    if user["id"]:
        try:
            username = user["name"]
            userfile = await db_get_user_profile(username)
            permission_level = userfile["permission_level"]
            return permission_level
        except Exception as e:
            return f"Error retrieving permission level {e}"
    
    return "Unverfied token"

async def change_persmission_level(data, token):
    try: #checks if data is given in the right way
        target_user = data[0]
        new_access_level = data[1]
    except:
        return "Invalid data"
    target_userfile = await db_get_user_profile(target_user) #gets target user profile
    if not target_userfile:
        return "Target user does not exist"

    profile = utils.get_user_profile(token) #gets session profile from token
    if profile: 
        username = profile["name"]
        userfile = await db_get_user_profile(username) #gets user profile 
        if userfile: #double checks if user has a server profile
            access_level = userfile["permission_level"] 
            if not "change_to_"+new_access_level in config["access_level"]:
                return "access_level does not exist"
            if access_level in config["access_level"]["change_to_"+new_access_level]:
                target_userfile["permission_level"] = new_access_level
                print(f"User {target_user} now has permission level {new_access_level}")
                return "Success"
            else:
                return "Not high enough access level to do this"
        else:
            return "Userprofile is missing"
    else:
        return "Invalid token"
