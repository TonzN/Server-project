import loads
loads.time.sleep(1)

for user in loads.users:
    loads.users[user]["chat_history"] = {"Users":{}, "Groups":{}}

with open(loads.users_path, 'w') as file:
    loads.users = loads.json.dump(loads.users, file, indent=4)
