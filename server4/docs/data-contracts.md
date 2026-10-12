# Server 4 data contracts

All examples are descriptive of the **Server 3-compatible implementation**.
They are not invitations to send arbitrary server-internal objects.

## 1. Incoming WebSocket packet
`datapacket_manager.Packet` uses Pydantic:

```json
{"v":1,"action":"ping","data":"ping","tag":"req-42","token":"<jwt>"}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `v` | integer, exactly `1` | Packet schema version (defaults to 1) |
| `action` | string | Key in `config["function_keys"]`, e.g. `ping`, `join_room` |
| `data` | any JSON value | Handler-specific payload; e.g. `["alice"]` for join_room |
| `tag` | string | Client-supplied correlation identifier, echoed in reply |
| `token` | JWT string or null | Server-generated token, used to obtain session |

Access after parsing: `packet.action`, `packet.data`, `packet.tag`,
`packet.token`. To create a new request, use those **same** JSON field names.
`validate_packet(raw, packet_type)` currently ignores its second argument and
returns `Packet` or `False`.

## 2. Outgoing envelope
`server_manager.create_reponse(payload, tag)` delegates to
`data_contracts.build_response`:

```json
{"data":["pong","req-42"]}
```

The serialized WebSocket message includes a final newline (`\\n`).
`data[0]` is the result, `data[1]` is the originating tag. The dispatcher
often converts returned Python values to **strings** before serialization.
Do not replace it with a new format until clients have migrated.

For unsolicited chat pushes the existing implementation also sends a
`{"data": [{"user": "...", "message": "...", "signal":"chat"}, "chat"]}`
envelope. Read the message as `packet["data"][0]["message"]`.

## 3. Persistent user: PostgreSQL `users` table
The implemented creation/insertion path expects:

```python
database_user = {
    "username": "alice",
    "password": "<argon2 hash>",
    "id": "00042",
    "permission_level": "basic",
    "security_mode": "normal",
}
username = database_user["username"]
database_user["permission_level"] = "admin"   # local mutation only
```

| Field | Meaning |
| --- | --- |
| `username` | Account identifier / lookup key |
| `password` | Argon2 password hash |
| `id` | Server-generated, zero-padded string identifier |
| `permission_level` | Role such as `basic` or `admin` |
| `security_mode` | Stored account security mode |

Read a user with `await db_get_user_profile("alice")`. Update one column
with `await db_add_user_data("alice", "permission_level", "basic")`.
In Server 3's original `create_user`, the profile key is written as
`securitymode` (no underscore), while SQL uses `security_mode`: **this is an
inherited inconsistency**, not an approved schema change. `create_user` also
omits an `await` on insertion; do not assume creation succeeds.

## 4. Active session: `_user_profiles` memory cache
Key: `session_key` from the validated JWT, value:

```python
session = {
    "name": "alice",
    "id": "00042",
    "connection_error_count": 0,
    "heartbeat": 1720000000.0,
    "socket": websocket,           # live socket, NOT JSON
    "subscribed_room": None,       # room ID or group name
    "rooms_joined": [],            # historical [room_key, room_id] pairs
}
```

| Field | Type | Purpose |
| --- | --- | --- |
| `name` | str | Username from database |
| `id` | str | Account ID |
| `connection_error_count` | int | Session-level error counter |
| `heartbeat` | float | `time.time()` of last accepted ping |
| `socket` | WebSocket object | Actual connection, server-private |
| `subscribed_room` | str or None | Current DM room ID / group label |
| `rooms_joined` | list of two-element lists | Legacy room cleanup metadata |

Construct only with `build_session_profile(database_user, socket, time.time())`
on the new code path. Obtain a session with `get_user_profile(token)`, which
verifies JWT and looks up `session_key` in `_user_profiles`:

```python
profile = get_user_profile(token)
if profile:
    current_room = profile.get("subscribed_room")
    profile["subscribed_room"] = "01234"
    profile["heartbeat"] = time.time()
```

`add_profile(session_key, profile)` and `remove_profile(session_key)`
write/remove the in-memory session; **they do not update PostgreSQL**.

## 5. Other server-side registries
All live in `database_manager.py`:

| Registry | Key | Value | How to read/change |
| --- | --- | --- | --- |
| `_online_users` | username | WebSocket | `get_user`, `add_user`, `remove_user` |
| `_user_profiles` | JWT session key | Session dict | `get_profile`, `add_profile`, `remove_profile` |
| `_groups` | group name | `GroupChat` object | `get_group`, `add_group`, `remove_group` |
| `_user_room2` | `str(sorted([user1,user2]))` | room ID | `get_2user_room_id`; created via `create_2user_room` |
| `_rooms` | DM room ID | Room dict | `get_2user_room`, `join_2user_room`, `leave_2user_room` |
| `_room_invites` | username | invite dictionary | `get_room_invite`, `add_room_invite` |

A DM room contains `{"users": ["alice","bob"], "active_users": {"alice"}}`.
`users` is a **list** of participants, `active_users` is a **set** of currently
joined participants. Both are Python objects, not wire JSON. Example:

```python
room = get_2user_room("01234")
if room and "bob" in room["users"]:
    room["active_users"].add("bob")
```

Do not directly modify registries from a new module if a manager function
already exists.

## 6. DM send and message storage
Client command `message_user` expects `data=["bob", "hello"]`.
The sender is the authenticated session's `name`. A successful real-time push
uses an envelope described in section 2. Persistent messages are inserted with:

```python
await db_add_message(["alice", "bob", "hello"])
```

The SQL inserts `(sender, receiver, message)`; PostgreSQL supplies other
columns (such as `message_id` and `timestamp`, if configured). Fetch:

```python
history = await db_get_messages_from_user_to("alice", "bob")
for record in history or []:
    print(record["sender"], record["message"])
```

The current code returns before storing if the recipient is offline or not in
the active DM room, despite a contradictory docstring. Treat offline delivery
as **not currently guaranteed**, not a feature.

## 7. Group and chat history
`GroupChat("global")` has `name` (string), and `users` (dictionary keyed
by username). Add via `group.add_user({"name":"alice"})` and remove via
`group.remove_user("alice")`.

Chat history queries return asyncpg records which `serialize_record` converts
to dictionaries, converting datetime `timestamp` to ISO 8601 strings. A
history response payload resembles:

```python
{"user": "bob", "message": [{"sender":"alice", "receiver":"bob",
    "message":"hello", "timestamp":"2026-10-12T15:00:00"}], "signal":"chat"}
```

Actual keys also depend on the PostgreSQL table schema. The outer WebSocket
wrapper might contain a **stringified** version of the above object.

## 8. Extending data safely
Add a field to the appropriate internal TypedDict in `data_contracts.py`,
initialize it in its builder, document its lifecycle, and update only the code
that owns it. **Do not add/remove fields from client packets, persistent SQL
rows or response payloads** until a separately approved protocol/schema change.
