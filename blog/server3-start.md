### Communication platform, v3.0 

## Introduction
The development of this project started as a simple local hosted server and clients accessing via console based client, it started as a simple project to see if i was able to do realtime communication and quickly developed past that. 
After some tweaking i developed a basic QT interface and cloud hosting this lead me to the second build of the project. 

The second build had a lot of issues rooting from trying to build of my first version and it wasnt sustainable to keep developing on the same code, this led me to build server 3 which was a totall restructering aiming to host a sustainable server. 

# Server 3

## Server 3 content

# Server Manager
Async

Keeps tracks of all client connections and websockets running them async

Login

New user creation

Client disconnection

Request handling

# Database
Build 3 uses a postgreSQL databased hosted on amazon EC2
To connect to this database you aquire a connection thru db_pool_manager.py
A connection can be aquired like this
``` 
await database_manager.server_pool.initialize()
db_connection = await database_manager.test_db()
```

The pool manager automatically aquires and releases connections to the database and manages pool size and initialziation

Aquiring data is done thru the database_manager.py 
The database manager lets you store file on json files and aquire and store data on the database.
Example of usage

```
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
``` 

```
@with_db_connection -> a decorator that handles getting and releasing connection to database
```

# Utils

Password hashing

JWT token authentication

db format data to json format and vise versa

User profile fetching

# Request Manager

Handles client requests to the server, this is where requests that isnt messages is handled.

# Message Manager

Handles messaging logic, dms, group chats, logging, logg fetching.

# Security Manager

Manager to verify and authenticate clients in a secure way

