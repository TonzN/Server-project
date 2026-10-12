# Server 4 — compatibility-first refactor

Server 4 is an incremental standardisation of `server3`. The primary constraint
is **no client-facing protocol or data-flow changes without explicit approval**.

## Current status
- Runtime implementation has been copied from the active Server 3 modules.
- Session-profile construction and response-envelope construction now use
  `data_contracts.py`, preserving all previous field names and values.
- Configuration and data paths point to `server4/`.
- Network requests still use the same `action`, `data`, `tag`, `token` keys,
  the same config-driven routing and the same responses.
- No claim of runtime compatibility verification: a runnable client was not
  present in this branch and no live PostgreSQL integration tests were run.
- Existing Server 3 implementation defects are intentionally **not** silently
  fixed when that could change behaviour.

## Reading the documentation
See [Data contracts](docs/data-contracts.md), [Data flow](docs/data-flow.md),
[Development standard](docs/standards.md), and [Compatibility notes](docs/compatibility.md).

## Running
From the repository root (with the original Python dependencies installed and
a configured PostgreSQL database):

```bash
python server4/server_manager.py
```

The database connection settings in `db_pool_manager.py` are still inherited
from Server 3 and should be moved to environment variables before deployment.
The inherited `users.json` is a legacy compatibility fixture, not the source
of truth for authenticated users; PostgreSQL stores persistent user profiles.

Existing root launcher scripts still target older versions and are not changed
by this refactor. Do not deploy Server 4 as a drop-in production replacement
until a known-good client has passed compatibility checks.
