# Server 4 development standard

## Goal
Make new code predictable without changing the externally visible protocol.

1. Keep **wire fields** unchanged: `v`, `action`, `data`, `tag`, `token`.
   Keep the response `{"data": [payload, tag]}\n`. Server 3 sometimes
   stringifies results before wrapping them: preserve this behaviour.
2. Use **snake_case** for new Python names, **PascalCase** for classes and
   **UPPER_SNAKE_CASE** for constants. Do not rename config action keys or
   persistent database columns just for style.
3. Use type hints for new functions and TypedDict/Pydantic for documented
   shapes. The Python annotation does not validate runtime payloads;
   validate at trust boundaries.
4. A manager module owns one concern. `server_manager` handles sockets and
   routing, `request_manager` handles client commands and rooms,
   `message_manager` handles chat actions, `database_manager` handles
   persistence/cache, `security_manager` handles authorization.
5. New operations must have a docstring stating accepted fields, return
   values, session mutations, DB writes and error cases.
6. Never put a live WebSocket into a network response or persistent row.
7. Obtain the authenticated username from the server-side session profile,
   **not** an untrusted `data.sender`.
8. Prefer `async def` for I/O and always `await` coroutines; verify how
   `async_function_keys` dispatches before changing any handler.
9. Parameterize SQL values. Identifiers require explicit validation/allowlists.
10. Changes to wire structure, existing action semantics, error strings,
    login sequence or room delivery order require approval plus regression tests.

## Migration boundary
`data_contracts.py` is the canonical reference for new internal data shapes.
Existing private functions retain their names/signatures where changing them
would create a risk. Gradual adoption is expected; this is **not** a completed
whole-repository style rewrite.

## Planned compatibility regression tests
- Existing client connects and receives the same `join_protocol` packet.
- Verify/register + `set_user` handshake keeps the same two-step sequence.
- `ping` returns `pong`; timeout still follows heartbeat logic.
- Online users, DM join/leave, DM delivery, group delivery and history retrieval
  preserve structure and ordering.
- Error responses, newline framing, tag round-tripping and byte/string sends
  remain compatible.
