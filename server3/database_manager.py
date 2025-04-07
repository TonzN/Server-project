from loads import *
import group_manager
import asyncpg as pg


class PoolManager:
    """Manages multiple database connection pools.  """
    def __init__(self):
        self._pools = {}

    def add_pool(self, name, pool):
        if name not in self._pools:
            self._pools[name] = pool
        else:
            raise RuntimeError("PoolManager->add_pool->Pool already exists")

    def get_pool(self, name):
        if name in self._pools:
            return self._pools[name]
        else:
            raise RuntimeError("Pool not found")
        
async def setup_db_connectionpool():
    """Set up a connection pool to the database.  """
    try:
        pool = await pg.create_pool(
            host="database.cf0yoiaesmqc.eu-north-1.rds.amazonaws.com",
            port="5432",
            user="postgres",
            password="toniNyt05#2030",
            min_size = 1,   
            max_size = 10
        )
        return pool
        
    except Exception as e:
        print(f"setup_db_connectionpool->Database connection pool error: {e}")
        return None

def with_db_connection(func):
    """Decorator to manage database connections.  """
    async def wrapper(_db_pool, *args, **kwargs):
        if _db_pool is None:
            raise RuntimeError("DB pool not initialized")
        try:
            async with _db_pool.acquire() as conn:
                return await func(conn, *args, **kwargs)
        except Exception as e:
            print(f"with_db_connection->Error in database operation: {e}")
    return wrapper

def get_connection(_db_pool):
    """
    Get a connection from the database pool."""
    try:
        if _db_pool is None:
            raise RuntimeError("DB pool not initialized")
        return _db_pool.acquire()
    except Exception as e:
        print(f"Error acquiring connection: {e}")   

def release_connection(_db_pool, conn):
    """Release a connection back to the database pool."""
    try:
        if _db_pool:
            _db_pool.release(conn)
    except Exception as e:  
        print(f"Error releasing connection: {e}")

def close_all_connections(_db_pool):
    """Close all connections in the database pool."""
    try:
        if _db_pool:
            _db_pool.close()
    except Exception as e:
        print(f"Error closing all connections: {e}")    


_online_users = {}
_user_profiles = {}

_groups = {"global": group_manager.GroupChat("global")}


#quick lookup for cached data
#--------------------------------------#
def get_all_online_users():
    return _online_users

def get_user(user):
    if user in _online_users:
        return _online_users[user]

def add_user(user, socket):
    _online_users[user] = socket

def remove_user(user):
    if user in _online_users:
        _online_users[user] = None
        del _online_users[user]

def get_profile(key):
    try:
        if key in _user_profiles:
            return _user_profiles[key]
        else:
            return False
    except Exception as e:
        print(f"Database->get_profile: {e}, key: {key}, profile: {_user_profiles}")
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

@with_db_connection
def db_get_user_profile(_db_pool, conn, id):
    try:
        return  conn.fetchrow("SELECT * FROM users WHERE id = $1", id)  
    except Exception as e:
        print(f"db_get_user_profile->Error: {e}")
        return None

@with_db_connection
def db_add_user_profile(_db_pool, conn, username, password):
    try:
        return conn.execute("INSERT INTO users (username, password, email) VALUES ($1, $2, $3)", username, password)
    except Exception as e:
        print(f"db_add_user_profile->Error: {e}")
        return None