online_users = {}

def get_user(user):
    if user in online_users:
        return online_users[user]

def add_user(user, user_profile):
    online_users[user] = user_profile

def remove_user(user):
    online_users.pop(user)

