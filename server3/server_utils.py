from loads import *
from database_manager import *

secret_key = "ving78"
server_rsa_key = None
private_key = None
super_duper_secret_key = secret_key

ph = PasswordHasher()

blacklisted_tokens = {}
client_keys = { }

def hash_password(password):
    """Hashes a password using Argon2."""
    return ph.hash(password)  # Returns a hashed password

def verify_password(stored_hash, provided_password):
    """Verifies a password against the stored hash."""
    try:
        ph.verify(stored_hash, provided_password)  # Raises error if incorrect
        return True
    except:
        return False

def gen_user_id():
    creation_id = str(config["user_count"])
    id = ""
    for i in range(5-len(creation_id)):
        id += "0"
    id += creation_id
    config["user_count"]
    return id

def get_id(msg, token):
    user = get_user_profile(token)
    if user:
        username = user["name"]
        id  = user["id"]
        return f"#{id}"
    
    return "Unverfied token"

def generate_token():
    payload = {
    "session_key": str(uuid.uuid4()),
    "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)  # Token expires in 1 hour
    }
    # Encode the token
    token = jwt.encode(payload, super_duper_secret_key, algorithm='HS256')
    return token

def invalidate_token(token):
    blacklisted_tokens[token] = token

def validate_token(token):
    try:
        if token not in blacklisted_tokens:
            payload = jwt.decode(token, super_duper_secret_key, algorithms=["HS256"])
            return payload  # If successful, return the token payload
    except jwt.ExpiredSignatureError:
        print("Token expired.")
        return None
    except jwt.InvalidTokenError:
        print("Invalid token.")
        return None

def get_user_profile(token):
    """Get user profile from token if its validated.
       Returns False if token is invalid or expired.
       Token payload gives you the payload used to retrieve the user profile from a session_key"""
    try:
        payload = validate_token(token)
        if payload:
            session_key = payload["session_key"]
            profile = get_profile(session_key)
            if profile:
                return profile
            else:
                return False
        else:
            print(f"INVALID TOKEN {token}")
            return False
    except Exception as e:
        print(f"Error: get_user_profile: {e}")
        return False

def json_to_arr_ordered(json_data, field_order):
    """Convert JSON data to a table format. Only for tranfering json to db
       Order of array is determined by field_order
       json_data: dict or list of dicts"""
    try:
        if type(json_data) == list:
            #returns array of users with data ordered by field_order
            return [[user.get(field, None) for field in field_order] for user in json_data]
        elif type(json_data) == dict:
            #returns array ordered by field_order 
            return [json_data.get(field, None) for field in field_order]
        
    except Exception as e:
        print(f"Error: json_to_arr_ordered: {field_order}, {json_data}, Exception: {e}")
        return False

def db_to_json(db_data):
    """Convert db data back to json format
       db_data: dict or list of dicts"""
    pass

