import loads
import database_manager
import server_utils
import asyncio

loads.time.sleep(1)

update_db = True

async def update_users():
    users = [database_manager.get_user_json_profile(user) for user in database_manager.get_all_users_json_profile()]
    ordered_users = server_utils.json_to_arr_ordered(users, ("username", "password", "id", "permission_level", "securitymode"))  
    print("\n\tUpdating users\n")
    print(ordered_users)
    await database_manager.db_add_multiple_user_profile(ordered_users)

async def add_messanges_table():
    print("\nCreating messages table...\n")
    column_defs = {
        "sender": "VARCHAR(200)",
        "receiver": "VARCHAR(200)",
        "message": "TEXT",
        "timestamp": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "message_id": "INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY",
        "encrypted": "BOOLEAN DEFAULT FALSE",
    }
    await database_manager.db.create_table("messages", column_defs)


if update_db:
    async def run_update():
         
        await database_manager.server_pool.initialize()
        db_connection = await database_manager.test_db()
        if not db_connection:
            print("Could not connect to database, closing server")
            return
        print("Connected to database")
        await add_messanges_table()
       
    asyncio.run(run_update())

update_json_data = False
if update_json_data:
    for user in loads.users:
        del loads.users[user]["chat_history"]

    with open(loads.users_path, 'w') as file:
        loads.users = loads.json.dump(loads.users, file, indent=4)
