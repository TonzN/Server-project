from loads import *


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
