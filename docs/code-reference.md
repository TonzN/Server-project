# Kodeguide — sentrale mekanismer

Alle utdrag er fra `server3/` i `unified-main` (forkortet der det står `...`).

## 1. Innkommende forespørsel og dynamisk dispatch

I `server_manager.client_recieve_handler()`:

```python
data = await asyncio.wait_for(websocket.recv(), timeout=recieve_timout)
packet = dp.validate_packet(data, dp.Packet)
function = packet.action
msg = packet.data
tag = packet.tag
token = packet.token
```

Serveren leser én WebSocket-melding med tidsgrense og dekoder JSON mot `Packet`-modellen. Etterpå sjekker den om action finnes i `func_keys`, og bruker navnet fra konfigurasjonen i `globals()` til å finne Python-funksjonen. Det er konfigurasjonens map som avgjør hvilke handlere klienter kan kalle.

```python
if function in message_function_keys:
    response = str(await globals()[func_keys[function]](msg, token))
elif function in async_function_keys and token:
    response = str(await globals()[func_keys[function]](msg, token))
elif token:
    response = str(globals()[func_keys[function]](msg, token))
```

**Konsekvens:** Hvis en `async def` ikke er merket async i config, returneres et coroutine-objekt uten å bli kjørt. Se `pull_user_chat_history_to_user`.

## 2. Hent verifisert øktprofil

`server_utils.get_user_profile()` knytter den signerte sesjonsnøkkelen til serverens interne profil:

```python
payload = validate_token(token)
if payload:
    session_key = payload["session_key"]
    profile = get_profile(session_key)
    if profile:
        return profile
```

Kjeden er `JWT -> session_key -> _user_profiles -> brukerens interne tilstand`. Tokenet alene inneholder **ikke** brukerens navn, aktive rom eller WebSocket.

## 3. PostgreSQL-tilkobling med dekoratør

Fra `database_manager.py`:

```python
def with_db_connection(func):
    async def wrapper(*args, **kwargs):
        _db_pool = server_pool.get_pool("main_pool")
        if _db_pool is None:
            raise RuntimeError("DB pool not initialized")
        try:
            async with _db_pool.acquire() as conn:
                return await func(conn, *args, **kwargs)
        except Exception as e:
            print(f"with_db_connection->Error in database operation: {e}")
            raise
    return wrapper
```

Dekoratøren gjør at databasefunksjoner kan deklareres med `conn` som første parameter uten at den som kaller dem må administrere tilkoblinger. `async with` frigjør tilkoblingen tilbake til poolen etter operasjonen.

## 4. Parameterisert SQL

```python
@with_db_connection
async def db_add_message(conn, data):
    try:
        return await conn.execute(
            "INSERT INTO messages (sender, receiver, message) VALUES ($1, $2, $3)",
            *data
        )
    except Exception as e:
        print(f"db_add_message->Error: {e}")
        return None
```

`$1`–`$3` bindes som separate SQL-parametere. Det beskytter mot vanlige SQL-injeksjoner i *verdiene*. Merk at `except` returnerer `None`: et kall som ignorerer resultatet kan feilaktig tolke en mislykket lagring som vellykket.

## 5. Direktemeldinger og persistens

`message_user` henter øktprofil og mottakers socket, kontrollerer DM-rommet, sender til mottaker og *deretter* kaller `logg_message`. `logg_message` bygger:

```python
log = [profile["name"], target_user, msg]
await db_add_message(log)
```

Dette er koblingen mellom chatlogikken og PostgreSQL. Det er per i dag ingen kø for mottakere som er frakoblet, og ingen atomisk levering/lagring.

## 6. Heartbeat

```python
def ping(msg, token=None):
    if token:
        user = get_user_profile(token)
        if user:
            user["heartbeat"] = time.time()
            return "pong"
```

Heartbeat er en tidsstempelbasert *applikasjonsmekanisme*, ikke WebSocket ping/pong-rammer. `client_handler` overvåker samme felt.

## 7. Oversikt over nøkkelfunksjoner

| Fil | Funksjon | Rolle |
|---|---|---|
| `server_manager.py` | `main`, `run_server`, `client_handler` | Oppstart og livssyklus |
| `server_manager.py` | `login`, `set_client`, `safe_client_disconnect` | Øktkontroll og cleanup |
| `server_manager.py` | `client_recieve_handler`, `create_reponse` | Input, dispatch og output |
| `security_manager.py` | `verify_user`, `get_permission_level`, `change_persmission_level` | Identitet og tilgang |
| `server_utils.py` | `hash_password`, `verify_password`, `generate_token`, `validate_token` | Kryptografiske hjelpere |
| `request_manager.py` | `join_room`, `leave_room`, `join_group_chat`, `leave_group_chat`, `ping` | Bruker-/romoperasjoner |
| `message_manager.py` | `message_user`, `message_group`, `pull_*`, `logg_message` | Melding, historikk, lagring |
| `database_manager.py` | `get_user`, `get_profile`, `create_2user_room`, `switch2_user_room` | Minnecache og rom |
| `database_manager.py` | `db_get_user_profile`, `db_add_user_profile`, `db_add_message`, `db_get_messages_from_user_to` | SQL |
| `db_pool_manager.py` | `PoolManager`, `setup_db_connectionpool` | Tilkoblingspool |

Se kildekoden for komplette signaturer og varianter som er merket deprecated/legacy.
