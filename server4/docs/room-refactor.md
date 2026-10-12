# Room ownership and compatible fixes

All DM and group state now belongs to `group_manager.py`:

| Registry | Key | Stored value |
| --- | --- | --- |
| `_groups` | group name | `GroupChat` instance containing a `users` dictionary |
| `_rooms` | room ID | `{"users": list[str], "active_users": set[str]}` |
| `_user_room2` | `str(sorted([sender, receiver]))` | room ID |
| `_room_invites` | username | dict mapping invite keys to room IDs |

`request_manager.py` still exposes the **same** externally dispatched
`join_room`, `leave_room`, `join_group_chat`, `leave_group_chat`
handlers, but imports room primitives from `group_manager.py`. This retains
all positional request formats and return values. `message_manager.py`
uses `group_manager` for group lookups and automated DM assignments.
`database_manager.py` focuses on online sessions and PostgreSQL.

## Fixed locally
- `create_user`: align `security_mode` key with SQL schema; await profile
  insert; do not report successful creation on failed insert.
- `change_persmission_level`: actually persist allowed role updates to
  PostgreSQL rather than mutating a temporary row dictionary.
- `set_client`: use the retrieved DB profile, not mere truthiness of
  legacy `users.json`, to guard session creation.
- Avoid printing raw tokens in normal diagnostics.
- Database connection arguments can be overridden with
  `SERVER4_DB_HOST`, `SERVER4_DB_PORT`, `SERVER4_DB_NAME`,
  `SERVER4_DB_USER`, `SERVER4_DB_PASSWORD`. Old development defaults are
  retained only to avoid an unexpected connection change.

## Security limitations (still outstanding)
- Legacy hard-coded JWT signing secret and fallback DB credentials
  must be **rotated/removed in a controlled deployment**, not silently.
- `kill_server` still relies on an older JSON-based admin check.
- No automated live-client integration or database tests were run.
- The existing login sequence and websocket action dispatch are unchanged.
- Existing room/session edge cases have not been fully redesigned.

Protocol contract remains **frozen** until the user approves migration.
