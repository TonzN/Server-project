# Authentication decorator and user data

Server 4 uses `auth_context.authenticated` for actions that operate on
**already logged-in** sessions. The WebSocket client still calls handlers
with exactly `(data, token)`; no request or response fields change.

```python
from auth_context import authenticated, UserContext

@authenticated(denied="my_action->invalid token")
def my_action(data, token, *, auth_user: UserContext):
    name = auth_user.username
    user_id = auth_user.id
    room = auth_user.session["subscribed_room"]
    return name
```

`auth_user.session` is a **mutable in-memory** profile, containing:
`name` (str), `id` (str), `socket` (WebSocket),
`heartbeat` (float UNIX timestamp), `subscribed_room` (str or None),
`rooms_joined` (list of [key, room_id] pairs),
`connection_error_count` (int).

Reading/updating:
```python
room = auth_user.session.get("subscribed_room")
auth_user.session["subscribed_room"] = "01234"
```

To retrieve persistent database fields, use the async form:
```python
@authenticated(database=True, denied="my_action->invalid token")
async def my_action(data, token, *, auth_user: UserContext):
    role = auth_user.account["permission_level"]
    return role
```

`auth_user.account` is a PostgreSQL row represented as a dictionary.
Expected fields: `username`, `password` (Argon2 hash),
`id`, `permission_level`, and `security_mode`.
The database is queried once per action only when `database=True`.

This decorator verifies identity, **not authorization**. Actions changing
other users' permissions still need role checks. Avoid passing the
`auth_user` object to client responses because it contains a live socket
and sensitive values.

### Exceptions
Pre-login actions (`veus`, `set_user`, `create_user`) must retain their
special handshake behavior. The decorator cannot be used before a session
exists. Functions handling disconnect/cleanup also have distinct inputs.

### Removed prototypes
Removed unused prototype helpers `message_manage`,
`parse_data_payload`, `logging`, `error_catching`,
`server_security`, `new_message_group`, `_auto_group`,
`old_message_user`, `friend_request`, `show_room_users`,
`_join_room`, `wait_for`, `get_dm_key`,
`update_user_json_profile`, `add_user_json_profile` and
`db_to_json`. Functions registered as public actions, along with
legacy JSON routines still referenced by active code, remain.

**Verification:** static review only. Client and PostgreSQL integration
tests have not been executed.
