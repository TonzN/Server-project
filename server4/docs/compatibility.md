# Compatibility notes and inherited issues

## Explicitly frozen
No changes to:
- `config.json` action keys or dispatch categories;
- request JSON fields or response envelope, including newline framing;
- JWT handshake order or client-facing action names;
- handler positional `data` layouts or observed return strings;
- DM/group routing logic, send-before-log order, or history representation.

## Changes in this commit
- New `server4/` copy of active `server3/` modules.
- `server4/loads.py` reads `server4/config.json` and
  `server4/users.json`.
- `server4/server_manager.py` builds the same session shape using
  `build_session_profile`, and wraps replies using `build_response`.
- New typed contracts and precise documentation.

## Known inherited issues — no behavioural fix applied
1. `create_user` uses `securitymode` internally but SQL insert expects
   `security_mode`, and does not await `db_add_user_profile`.
2. Config lists some async handlers in inconsistent categories: blindly
   normalizing dispatch can change results or cause unawaited coroutines.
3. Handler responses are stringified; changing them to structured JSON
   would break existing consumers.
4. `message_user` can skip logging when recipient is offline, despite its
   docstring; new offline-message semantics require product approval.
5. `new_message_group` is incomplete and `threadmanager.py` is an
   unfinished experimental component, not copied into the Server 4 runtime.
6. The inherited database pool configuration contains hardcoded credentials.
   These must be rotated and moved out of source control before deployment.
7. Server 3 uses a hard-coded JWT signing secret. This is inherited for
   compatibility only; rotate it with a controlled session migration.
8. `server4/users.json` is inherited as a compatibility file and must not be
   treated as a secure authoritative database. Check it for sensitive data
   before deploying or sharing.
9. No verified current client implementation is available on the branch;
   **runtime compatibility is not tested**.

These are documentation findings, not new regressions introduced by Server 4.
