import loads
loads.time.sleep(1)

for user in loads.users:
    loads.users[user]["friends"] = {}
    loads.users[user]["groups"] = {}
    loads.users[user]["blacklist"] = {}
    loads.users[user]["securitymode"] = "normal"
    loads.users[user]["friendrequests"] = {}
    loads.users[user]["preferences"] = {}

with open(loads.users_path, 'w') as file:
    loads.users = loads.json.dump(loads.users, file, indent=4)
