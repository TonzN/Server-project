import loads
import database_manager
import server_utils
import asyncio

loads.time.sleep(1)

users = [database_manager.get_user_json_profile(user) for user in database_manager.get_all_users_json_profile()]
ordered_users = server_utils.json_to_arr_ordered(users, ("username", "password", "id", "permission_level", "securitymode"))
print(ordered_users)
asyncio.run(database_manager.db_add_multiple_user_profile(ordered_users))


update_json_data = False
if update_json_data:
    for user in loads.users:
        del loads.users[user]["chat_history"]

    with open(loads.users_path, 'w') as file:
        loads.users = loads.json.dump(loads.users, file, indent=4)
