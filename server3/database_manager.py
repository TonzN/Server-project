from loads import *
import group_manager
from db_pool_manager import *

#temp cached data
_online_users = {}
_user_profiles = {}
_groups = {"global": group_manager.GroupChat("global")}

#centralised serverpool
server_pool = PoolManager()
"""pool for the main server, this is used to manage the connections to the database, "
"if you have multiple servers you can add more pools here"""
def with_db_connection():
    def _with_db_connection(func):
        """Decorator to manage database connections.  """
        async def wrapper(*args, **kwargs):
            _db_pool = server_pool.get_pool("main_pool") #get the pool
            if _db_pool is None:
                raise RuntimeError("DB pool not initialized")
            try:
                async with _db_pool.acquire() as conn:
                    return await func(conn, *args, **kwargs)
            except Exception as e:
                print(f"with_db_connection->Error in database operation: {e}")
        return wrapper
    return _with_db_connection

#--------------------------------------#
def wait_for(function, max_wait=5, *args, **kwargs):
    """ yields database manager until the function is successfull 
        Only use this for database initialization"""""
    start = time.time()
    while True:
        if time.time() - start > max_wait:
            break
        try:
            success = function(*args, **kwargs)
            if success:
                return success
        except Exception as e:
            print(f"wait_for->Error: {e}")
            return False
        time.sleep(0.1)
    
#quick lookup for cached data
#--------------------------------------#
def get_all_online_users():
    """Get all online users from the online users list
       Returns a list of all online users"""
    return _online_users

def get_user(user):
    """Get user from the online users list
       Returns the socket of the user if found"""
    if user in _online_users:
        return _online_users[user]

def add_user(user, socket):
    _online_users[user] = socket

def remove_user(user):
    """Remove user from the online users list
       Returns True if user was removed, False if user was not found"""
    if user in _online_users:
        _online_users[user] = None
        del _online_users[user]

def get_profile(key):
    """Get user profile from the user profiles list
       Returns the profile of the user if found"""
    try:
        if key in _user_profiles:
            return _user_profiles[key]
        else:
            return False
    except Exception as e:
        print(f"Database_manager->get_profile: {e}, key: {key}, profile: {_user_profiles}")
        return False

def add_profile(key, profile):
    try:
        _user_profiles[key] = profile
    except Exception as e:
        print(f"Could not add profile {e}")
        return False

def remove_profile(key):
    if key in _user_profiles:
        _user_profiles[key] = None
        del _user_profiles[key]

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

def get_user_json_profile(user):
    try: 
        if user in users_file:
            return users_file[user]
        else:
            return False
    except Exception as e:
        print(f"Could not retrieve user json profile {e}")
        return False

def get_all_users_json_profile():
    return users_file

def update_user_json_profile(user, profile): #depricated
    try:
        if user in users_file:
            users_file[user] = profile
        else:
            print(f"User {user} json file not found and could not be updated")
            return False
    except Exception as e:
        print(f"Could not update user profile {e}")

def add_user_json_profile(user, profile): #depricated
    try:
        users_file[user] = profile
    except Exception as e:
        print(f"Could not add user profile {e}")
        return False

def update_users_json_file(): #depricated
    try:
        with open(users_path, "w") as file:
            json.dump(users_file, file, indent=4)
    except Exception as e:
        print(f"Could not update users file {e}")
        return False

#Database management

#super cool algorithm to get frequently used data

#main_pool = wait_for(server_pool.get_pool, 0, "main_pool")
#if not main_pool:
 #   raise RuntimeError("Database_manager->waitfor(main_pool)-> Could not get main pool")

@with_db_connection()
async def db_get_user_profile(conn, username):
    """Get user profile from database. Connected by the pool manager"""
    try:
        isempty = await conn.fetch("SELECT * FROM users")
        if len(isempty) == 0: #for debugging incase the table is actually empty
            print("Table is empty, users template")
            rows = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'users'
            """)
            for r in rows:
                print(r)

        return  await conn.fetch("SELECT * FROM users WHERE username = $1", username)  
    except Exception as e:
        print(f"db_get_user_profile->Error: {e}")
        return None

@with_db_connection()
def db_add_user_profile(conn, user_data):
    """Add user profile to database. Connected by the pool manager.\n
       user_data = array or list of user data\n
       conn: automatically handled by the pool manager\n
       This is used for single inserts"""
    try:
        return conn.execute("INSERT INTO users "
        "(username, password, id, permission_level, securitymode) "
        "VALUES ($1, $2, $3, $4, $5)", *user_data)
    except Exception as e:
        print(f"db_add_user_profile->Error: {e}")
        return None

@with_db_connection()
def db_add_multiple_user_profile(conn, user_data):
    """
       Add user profile to database. Connected by the pool manager\n 
       user_data = array or list of user data\n
       conn: automatically handled by the pool manager\n
       This is used for bulk inserts"""
    try:
        return conn.executemany("INSERT INTO users "
        "(username, password, id, permission_level, securitymode) "
        "VALUES ($1, $2, $3, $4, $5)", user_data)
    
    except Exception as e:
        print(f"db_add_multiple_user_profile->Error: {e}")
        return None