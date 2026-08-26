from loads import *
import group_manager
from db_pool_manager import *
from psycopg2.extensions import quote_ident  # tiny helper
import server_utils as utils
import re


#temp cached data
_online_users = {} # online users are stored here
_user_profiles = {} # user profiles are stored here
_groups = {"global": group_manager.GroupChat("global")}
_user_room2 = {} # subscribed users to rooms will be stored here mapping room ids a_b = room id
_rooms = {} # rooms are stored here mapping room ids to room objects room_id = {users: [], invited: []}
_room_invites = {} # room invites are stored here mapping room ids to invited users user = {invite: room_id}


debug_room = False      

#centralised serverpool
server_pool = PoolManager()
"""pool for the main server, this is used to manage the connections to the database, "
"if you have multiple servers you can add more pools here"""

SAFE_TYPES = {
    "text", "varchar", "integer", "bigint", "timestamp",
    "timestamptz", "boolean", "jsonb", "varchar(200)", "varchar(100)", "varchar(50)", "varchar(20)", "varchar(10)"
}

whitelisted_tables = {
    "users", "messages", "groups", "rooms"
}

def _quote_ident(ident: str) -> str:
    """Validate and quote a PostgreSQL identifier."""

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", ident):
        raise ValueError(f"Invalid SQL identifier: {ident}")

    return f'"{ident}"'


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
            raise 
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

#--------------------------------------#
#Room management

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
    """Mark a user as no longer active in a room."""

    room = get_2user_room(room_id)

    if not room:
        return False

    room["active_users"].discard(user)

    return True

def get_2user_room(room_id):
    if debug_room:
        print(f"ALL ROOMS: {_rooms}") #??????????????
        for keys in _rooms:
            print("keys", keys)
            try:
                print(keys in _rooms)
            except Exception as e:                                    
                print(f"{e}")

    print("\n")
    if room_id in _rooms:
        return _rooms[room_id]
    else:
        print(f"get_2user_room->Error: Room {room_id} not found")
        return None

def create_2user_room(sender, receiver):
    try:
        room_key = get_dm_key(sender, receiver)

        if room_key in _user_room2:

            room_id = _user_room2[room_key]

            # Mapping finnes, men rommet mangler
            if room_id not in _rooms:

                print(
                    f"Room mapping existed but room {room_id} "
                    f"was missing. Recreating."
                )

                _rooms[room_id] = {
                    "users": [sender, receiver],
                    "active_users": {sender}
                }

                return "created", room_id

            _rooms[room_id]["active_users"].add(sender)

            return "found", room_id

        # Ingen mapping -> nytt rom
        room_id = str(utils.get_random_room_id())

        _user_room2[room_key] = room_id

        _rooms[room_id] = {
            "users": [sender, receiver],
            "active_users": {sender}
        }

        return "created", room_id

    except Exception as e:

        print(f"create_2user_room->Error: {e}")

        return "error", None
    
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

def get_dm_key(user1, user2):
    return tuple(sorted([user1, user2]))

#quick lookup for cached data
#--------------------------------------#
def get_room_invite(user):
    """Get room invite from the room invites list
       Returns the invite of the user if found"""
    if user in _room_invites:
        return _room_invites[user]

def add_room_invite(user):
    _room_invites[user] = {}

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
async def db_create_table(conn, table_name: str, column_defs: dict[str, str]):
    # 1. Whitelist table name (optional but cheap)
    if not table_name.isidentifier():
        raise ValueError("illegal table name")

    # 2. Validate column definitions
    cols_sql = []
    for col, col_type in column_defs.items():
        if not col.isidentifier():
            raise ValueError(f"bad column name {col!r}")
        if col_type.split()[0].lower() not in SAFE_TYPES:
            raise ValueError(f"disallowed type {col_type!r}")
    
        cols_sql.append(f"{_quote_ident(col)} {col_type}")

    ddl = (
        f"CREATE TABLE IF NOT EXISTS {_quote_ident(table_name)} "
        f"({', '.join(cols_sql)})"
    )
    await conn.execute(ddl)


@with_db_connection
async def db_get_table(
    conn,
    table_name: str,
    limit: int | None = None,
    order_by: str | None = None,   # e.g. "created_at"
    newest_first: bool = True
):
    """Get table from database.
       limit: number of rows (None = all)
       order_by: column name to order by (None = no ordering)
       newest_first: DESC if True else ASC (only used if order_by is set)
    """
    try:
        if table_name not in whitelisted_tables:
            print(f"db_get_table->Table {table_name} is not whitelisted")
            return None

        # Optional: validate order_by to avoid SQL injection via column name
        if order_by is not None:
            col_rows = await conn.fetch("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = $1
            """, table_name)
            cols = {r["column_name"] for r in col_rows}
            if order_by not in cols:
                print(f"db_get_table->Invalid order_by column: {order_by}")
                return None

        order_clause = ""
        if order_by is not None:
            direction = "DESC" if newest_first else "ASC"
            order_clause = f' ORDER BY "{order_by}" {direction}'

        if limit is None:
            query = f"SELECT * FROM {table_name}{order_clause}"
            rows = await conn.fetch(query)
        else:
            if limit <= 0:
                print("db_get_table->limit must be > 0")
                return None
            query = f"SELECT * FROM {table_name}{order_clause} LIMIT $1"
            rows = await conn.fetch(query, limit)

        if not rows:
            print("Table is empty, messages template")
            show = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'messages'
            """)
            for r in show:
                print(r)
            return None

        return [dict(r) for r in rows]

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

@with_db_connection
async def db_find_user_profile(conn, username):
    """Find user profile in database. Connected by the pool manager\n
       username = username of the user to find\n
       conn: automatically handled by the pool manager
       returns the user true if found, None if not found"""
    try:
        user = await conn.fetch("SELECT username FROM users WHERE username = $1", username)
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
        if not value.isidentifier():
            raise ValueError("Invalid column name")

        query = (
            f"UPDATE users "
            f"SET {_quote_ident(value)} = $1 "
            f"WHERE username = $2"
        )

        return await conn.execute(query, data, username)
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
        if not value.isidentifier():
            raise ValueError("Invalid column name")

        query = (
            f"SELECT {_quote_ident(value)} "
            f"FROM users WHERE username = $1"
        )

        return await conn.fetch(query, username)
    except Exception as e:
        print(f"db_get_value_from_user->Error: {e}")
        return None

@with_db_connection
async def db_get_messages_from_user_to(conn, sender, receiver):
    """Get messages from user to user in database. Connected by the pool manager\n
       sender = sender of the message\n
       receiver = receiver of the message\n
       conn: automatically handled by the pool manager"""
    try:
        return await conn.fetch("""SELECT * FROM messages 
        WHERE (sender = $1 AND receiver = $2)
           OR (sender = $2 AND receiver = $1)
        ORDER BY timestamp""", sender, receiver)
    except Exception as e:
        print(f"db_get_messages_from_user_to->Error: {e}")
        return "db_get_messages_from_user_to->Error: {e}"

@with_db_connection
async def db_get_all_messages_from(conn, username):
    """Get all messages from user in database. Connected by the pool manager\n
       username = username of the user to get messages from\n
       conn: automatically handled by the pool manager"""
    try:
        return await conn.fetch("SELECT * FROM messages WHERE receiver = $1", username)
    except Exception as e:
        print(f"db_get_all_messages_from->Error: {e}")
        return None

@with_db_connection
async def db_add_message(conn, data):
    """Add message to database. Connected by the pool manager\n
       sender = username of the sender\n
       recieve = username of the reciever\n
       message = message to add\n
       conn: automatically handled by the pool manager"""
    try:
        return await conn.execute("INSERT INTO messages "
        "(sender, receiver, message) "
        "VALUES ($1, $2, $3)", *data)
    except Exception as e:
        print(f"db_add_message->Error: {e}")
        return None

@with_db_connection
async def db_remove_message(conn, message_id):
    """Remove a message from database by id.
       conn: automatically handled by the pool manager
    """
    try:
        result = await conn.execute(
            "DELETE FROM messages WHERE message_id = $1",
            message_id
        )

        # result looks like: "DELETE 1" or "DELETE 0"
        deleted_count = int(result.split(" ")[1])

        if deleted_count == 0:
            print(f"db_remove_message->No message found with id {message_id}")
            return False

        return True

    except Exception as e:
        print(f"db_remove_message->Error: {e}")
        return False

@with_db_connection
async def db_get_all_messages_from_group(conn, group):
    """Get all messages from database. Connected by the pool manager\n
       conn: automatically handled by the pool manager"""
    try:
        return await conn.fetch("SELECT * FROM messages"
                                "WHERE group = $1", group)
    except Exception as e:
        print(f"db_get_all_messages_from_group->Error: {e}")
        return None

