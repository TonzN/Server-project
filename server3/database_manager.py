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


def with_db_connection(func):
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

@with_db_connection
async def db_create_table(conn, table_name, column_defs):
    """
    Create a table in the database if it doesn't exist.
    
    Args:
        conn: The database connection object.
        table_name: The name of the table to create.
        columns_defs: A dictionary, column name as key and column definition as value.
    """
    column_definitions = ", ".join(f"{col} {col_type}" for col, col_type in column_defs.items())
    create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_definitions})"
    await conn.execute(create_table_query)

@with_db_connection
async def db_get_table(conn, table_name):
    """Get table from database. Connected by the pool manager\n
       conn: automatically handled by the pool manager"""
    try:
        rows = await conn.fetch(f"SELECT * FROM {table_name}")
        if len(rows) == 0: #for debugging incase the table is actually empty
            print("Table is empty, messages template")
            show = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'messages'
            """)
            for r in show:
                print(r)
            return None
        else:
            return dict(rows[0])
        
    except Exception as e:
        print(f"db_get_table->Error: {e}")
        return None

@with_db_connection
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

        user = await conn.fetch("SELECT * FROM users WHERE username = $1", username)
        return  dict(user[0])
    except Exception as e:
        print(f"db_get_user_profile->Error: {e}")
        return None

async def db_find_user_profile(conn, username):
    """Find user profile in database. Connected by the pool manager\n
       username = username of the user to find\n
       conn: automatically handled by the pool manager
       returns the user true if found, None if not found"""
    try:
        user = conn.fetch("SELECT username FROM users WHERE username = $1", username)
        if user:
            return user
        else:
            return False
    except Exception as e:
        print(f"db_find_user_profile->Error: {e}")
        return None
@with_db_connection
async def db_update_user_profile(conn, user_data):
    """Update user profile in database. Connected by the pool manager\n
       user_data = array or list of user data\n
       conn: automatically handled by the pool manager\n
       This is used for bulk updates"""
    try:
        if user_data:
            return await conn.execute("UPDATE users "
            "SET username = $1, password = $2, id = $3, permission_level = $4, security_mode = $5 "
            "WHERE username = $6", *user_data, user_data[0])
        else:
            print("No user data to update")
            return False
    except Exception as e:
        print(f"db_update_user_profile->Error: {e}")
        return None

@with_db_connection
async def db_add_user_data(conn, username, value, data):
    """Add user data to database. Connected by the pool manager\n
       username = username of the user to add data to\n
       value = key to add data to\n
       data = data to add\n
       conn: automatically handled by the pool manager"""
    try:
        return await conn.execute("UPDATE users SET $1 = $2 WHERE username = $3", value, data, username)
    except Exception as e:
        print(f"db_add_user_data->Error: {e} \n username: {username}, value: {value}, data: {data}")
        return None
    
@with_db_connection
async def db_add_user_profile(conn, user_data):
    """Add user profile to database. Connected by the pool manager.\n
       user_data = array or list of user data\n
       conn: automatically handled by the pool manager\n
       This is used for single inserts"""
    try:
         return await conn.execute("INSERT INTO users "
        "(username, password, id, permission_level, security_mode) "
        "VALUES ($1, $2, $3, $4, $5)", *user_data)
    except Exception as e:
        print(f"db_add_user_profile->Error: {e}")
        return None

@with_db_connection
async def db_add_multiple_user_profile(conn, user_data):
    """
       Add user profile to database. Connected by the pool manager\n 
       user_data = array or list of user data\n
       conn: automatically handled by the pool manager\n
       This is used for bulk inserts"""
    try:
        return await conn.executemany("INSERT INTO users "
        "(username, password, id, permission_level, security_mode) "
        "VALUES ($1, $2, $3, $4, $5)", user_data)
    
    except Exception as e:
        print(f"db_add_multiple_user_profile->Error: {e}")
        return None

@with_db_connection
async def db_update_user_profile(conn, user_data):
    """Update user profile in database. Connected by the pool manager\n
       user_data = array or list of user data\n
       conn: automatically handled by the pool manager\n
       This is used for bulk updates"""
    try:
        return await conn.executemany("UPDATE users "
        "(username, password, id, permission_level, security_mode) "
        "VALUES ($1, $2, $3, $4, $5) WHERE username = $username", user_data, user_data[0])
    
    except Exception as e:
        print(f"db_update_user_profile->Error: {e}")
        return None

@with_db_connection
async def db_delete_user_profile(conn, username):
    """Delete user profile from database. Connected by the pool manager\n
       username = username of the user to delete\n
       conn: automatically handled by the pool manager"""
    try:
        return await conn.execute("DELETE FROM users WHERE username = $1", username)
    except Exception as e:
        print(f"db_delete_user_profile->Error: {e}")
        return None

@with_db_connection
async def db_get_all_user_profile(conn):
    """Get all user profiles from database. Connected by the pool manager\n
       conn: automatically handled by the pool manager"""
    try:
        return await conn.fetch("SELECT * FROM users")
    except Exception as e:
        print(f"db_get_all_user_profile->Error: {e}")
        return None

@with_db_connection
async def db_get_value_from_user(conn, value, username):
    """Get value from user profile in database. Connected by the pool manager\n
       key = key to get from the user profile\n
       conn: automatically handled by the pool manager"""
    try:
        return await conn.fetch("SELECT $1 FROM users WHERE username = $2", value, username)
    except Exception as e:
        print(f"db_get_value_from_user->Error: {e}")
        return None

@with_db_connection
async def db_get_messages_from_user_to(conn, sender, reciever):
    """Get messages from user to user in database. Connected by the pool manager\n
       sender = sender of the message\n
       reciever = reciever of the message\n
       conn: automatically handled by the pool manager"""
    try:
        return await conn.fetch("SELECT * FROM messages WHERE sender = $1 AND reciever = $2", sender, reciever)
    except Exception as e:
        print(f"db_get_messages_from_user_to->Error: {e}")
        return None

@with_db_connection
async def db_get_all_messages_from(conn, username):
    """Get all messages from user in database. Connected by the pool manager\n
       username = username of the user to get messages from\n
       conn: automatically handled by the pool manager"""
    try:
        return await conn.fetch("SELECT * FROM messages WHERE sender = $1", username)
    except Exception as e:
        print(f"db_get_all_messages_from->Error: {e}")
        return None

@with_db_connection
async def db_add_message(conn, data):
    """Add message to database. Connected by the pool manager\n
       sender = username of the sender\n
       reciever = username of the reciever\n
       message = message to add\n
       conn: automatically handled by the pool manager"""
    try:
        return await conn.execute("INSERT INTO messages "
        "(sender, reciever, message) "
        "VALUES ($1, $2, $3)", *data)
    except Exception as e:
        print(f"db_add_message->Error: {e}")
        return None

@with_db_connection
async def db_get_all_messages_from_group(conn, group):
    """Get all messages from database. Connected by the pool manager\n
       conn: automatically handled by the pool manager"""
    try:
        return await conn.fetch("SELECT * FROM messages"
                                "WHERE group = $1", group)
    except Exception as e:
        print(f"db_get_all_messages->Error: {e}")
        return None

