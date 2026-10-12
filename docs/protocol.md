# WebSocket-protokoll og API

## Innkommende pakker

Modellen `Packet` i `datapacket_manager.py` beskriver følgende JSON-struktur:

```json
{
  "v": 1,
  "action": "ping",
  "data": "ping",
  "tag": "request-42",
  "token": "<JWT_FROM_JOIN_PROTOCOL>"
}
```

| Felt | Type | Beskrivelse |
|---|---|---|
| `v` | `Literal[1]` | Versjon (standard 1) |
| `action` | `str` | Navn på kommando fra `function_keys` |
| `data` | `Any` | Payload (streng, liste eller objekt avhengig av handling) |
| `tag` | `str` | Klientvalgt korrelasjons-ID/merkelapp |
| `token` | `str` eller `null` | JWT-token knyttet til tilkoblingen |

Pydantic validerer at påkrevde felt finnes, men `data: Any` gir **ikke** schemaspesifikk validering per action. `validate_packet(data, packet_type)` tar inn en `packet_type`-parameter, men bruker alltid `Packet` direkte i implementasjonen.

## Utgående svar

Dette er den *faktisk brukte* hjelpefunksjonen:

```python
def create_reponse(data, tag):
    packet = json.dumps({"data": [data, tag]}) + "\n"
    return packet
```

Et vanlig svar ser slik ut:

```json
{"data": ["pong", "request-42"]}
```

I praksis blir returverdier fra handlere ofte først omsatt til `str(...)`, og så JSON-kodet i `create_reponse`. Derfor kan komplekse objekter komme tilbake som **tekst som ligner Python-dictionary**, ikke som JSON-objekter. Den definerte `ResponsePacket`-modellen brukes ikke konsekvent av senderen.

## Handlingskartet

Tabellen følger `server3/config.json` på `unified-main`; **registrert** betyr ikke nødvendigvis **fungerer**.

| `action` | Mål i `function_keys` | Formål | Merk |
|---|---|---|---|
| `veus` | `verify_user` | Verifiser brukernavn/passord | async |
| `set_user` | `set_client` | Opprett serverintern økt | async; socket i klientdata er problematisk |
| `create_user` | `create_user` | Registrer bruker | async; DB-kall mangler `await` |
| `ping` | `ping` | Oppdater heartbeat | synkron |
| `get_id` | `get_id` | Hent egen bruker-ID | synkron funksjon, men listet som async |
| `get_permission_level` | `get_permission_level` | Slå opp tilgang | async |
| `change_permission_level` | `change_persmission_level` | Endre tilgang | async; lagring til DB mangler |
| `show_online_users` | `show_online_users` | Online-brukere | synkron |
| `kill_server` | `kill_server` | Administrativ stopp | synkron; risikabel |
| `message_user` | `message_user` | Send DM | async |
| `message_group` | `message_group` | Send gruppemelding | async |
| `pull_chat_history` | `pull_group_chat_history` | Historikk | Mål mangler i gjennomgått `message_manager.py` |
| `pull_user_chat_history_to_user` | samme | DM-historikk | async, men ikke listet i async-settet |
| `pull_all_chat_history` | samme | Global historikk | async |
| `join_room` | `join_room` | DM-rom | synkron |
| `leave_room` | `leave_room` | Forlat DM-rom | synkron |
| `join_group_chat` | `join_group_chat` | Bli med i gruppe | synkron |
| `leave_group_chat` | `leave_group_chat` | Forlat gruppe | synkron |

Dispatcheren bruker tre konfigurasjonssett: `function_keys`, `async_function_keys` og `message_function_keys`. For handlinger i `message_function_keys` gjøres `await`; ellers gjøres `await` dersom handlingen finnes i `async_function_keys` og har token; resterende kall kjøres synkront. **Denne strukturen krever konsistens mellom konfig og `async def`-deklarasjon.**

## Direktemeldinger

Innkommende payload for `message_user` er `[mottaker, melding]`, for eksempel:

```json
{
  "v": 1,
  "action": "message_user",
  "data": ["mottaker", "Hei!"],
  "tag": "msg-1",
  "token": "<JWT>"
}
```

Ved direkte levering sendes i tillegg en separat hendelse til mottakerens WebSocket:

```json
{"data": [{"user": "avsender", "message": "Hei!", "signal": "chat"}, "chat"]}
```

Dette er forskjellig fra svaret avsenderen mottar. Formatet som vises er hentet fra kildekoden; det er **ikke** bevis for vellykket ende-til-ende-testing.

[Kilde: datapacket_manager.py](https://github.com/TonzN/Server-project/blob/unified-main/server3/datapacket_manager.py) · [config.json](https://github.com/TonzN/Server-project/blob/unified-main/server3/config.json)
