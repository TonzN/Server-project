# Sikkerhet, status og kjente avvik

Dette er en **kildekodegjennomgang**, ikke en penetrasjonstest. Punktene under er konkrete observasjoner i `server3` i `unified-main`. Prosjektet er ikke verifisert ved integrasjonstesting her.

## Kontroller som er implementert

- Passord hashes og verifiseres med **Argon2** (`PasswordHasher` i `server_utils.py`).
- JWT (`HS256`) har `session_key` og én times utløp, samt et in-memory register over ugyldiggjorte token.
- SQL-verdier sendes vanligvis som **parameterisert input** til `asyncpg`.
- `db_get_table()` har whitelist for tabellnavn og kontrollerer sorteringskolonne mot PostgreSQL-katalogen.
- Handlingsnavn begrenses av konfigurasjonens `function_keys`.
- Det finnes egne konseptuelle rolle-/rettighetsnivåer (`basic`, `admin`).

## Kritiske og viktige forhold å rette

| Prioritet | Observasjon | Anbefalt handling |
|---|---|---|
| Kritisk | JWT-signering bruker en hardkodet hemmelighet i `server_utils.py`. | Roter nøkkelen, last fra beskyttet miljøvariabel og gjør token ugyldige ved kompromittering. |
| Kritisk | PostgreSQL-tilkoblingsdetaljer, inkludert passord, ligger i `db_pool_manager.py`. | Roter legitimasjon, bruk hemmelighetslager/miljøvariabler og minste privilegium. |
| Høy | `set_client()` stoler på `userdata["socket"]`, mens socket ikke kan representeres som JSON-WebSocket-objekt. | Bind til den serveraksepterte `websocket` fra `client_handler`, ikke klientinnhold. |
| Høy | `create_user()` kaller asynkrone `db_add_user_profile()` **uten `await`** og returnerer likevel status 1. | `await` DB-kallet og kontroller faktisk resultat før suksess. |
| Høy | `get_id` står i `async_function_keys`, men `get_id` er synkron. | Rett konfigurasjon eller implementasjon. |
| Høy | `pull_user_chat_history_to_user` er `async def`, men mangler i `async_function_keys` og `message_function_keys`. | Registrer som async. |
| Høy | `pull_chat_history` peker til `pull_group_chat_history`, som ikke finnes i den gjennomgåtte modulen. | Implementer/endre mapping. |
| Høy | `change_persmission_level` endrer bare dictionaryen som er hentet fra DB. Ingen DB-UPDATE blir utført. | Oppdater via autorisert DB-spørring og bekreft resultat. |
| Høy | Meldinger til offline bruker returnerer tidlig uten å bli lagret; lagring skjer etter socket-send. | Lagre først, håndter offline leveranse eksplisitt og innfør leveringsstatus. |
| Høy | `client_handler()` inneholder en f-string med kolliderende anførselstegn rundt `profile["name"]`, som gir syntaksfeil i relevante Python-versjoner. | Bruk konsistente forskjellige anførselstegn og kjør `python -m compileall server3`. |
| Høy | `server_manager.py` kaller `update_users_json_file()` ved disconnect; dette er eldre filbasert håndtering. | Gjør opprydding uavhengig av eldre JSON-brukerlagring. |
| Middels | `join_group_chat` leser `group_chat.name` før den kontrollerer om `group_chat` er `None`. | Valider objekt før oppslag. |
| Middels | `new_message_group` setter `room = None`, mens logikken krever `room == "global"`. | Fullfør eller fjern uferdig alternativ; avklar aktiv gruppemeldingsfunksjon. |
| Middels | `user_capacity` lastes, men ingen robust kapasitetssperre ses i oppkoblingsløkken. | Håndhev aktiv øktgrense og rate limiting. |
| Middels | Blacklist over tokens ligger bare i minne. | Ved flerprosess-/flerserverdrift: sentraliser tilbakekalling eller bruk kortlevde tokens. |
| Middels | Serveren skriver `wss://`, men kaller `websockets.serve()` uten `ssl`. | Bruk verifisert TLS-terminering eller SSL-context; dokumenter faktisk endepunkt. |
| Middels | `threadmanager.py` er vesentlig ufullstendig (`pass`), og har referanser til attributter/metoder som ikke er definert. | Ikke presenter den som en ferdig scheduler. |

## Andre implementasjonsavvik

- `verify_user()` bruker `get_user_profile(token)` til å sjekke allerede opprettet økt, ikke et fullstendig sentralt søk på alle innloggede brukernavn.
- `get_user_profile(token)` logger ugyldige token i klartekst. Unngå å skrive hemmeligheter til logger.
- `create_reponse()` serialiserer handlerrespons som ofte er konvertert med `str()`. Dette bryter forventningen om maskinlesbare JSON-objekter.
- Kommentarer som sier «offline messages will still store» stemmer ikke med den nåværende `message_user`-grenen.
- `gen_user_id()` bruker telling fra konfigurasjon; det bør erstattes med en unikhetsgarantert DB-nøkkel.
- Det finnes `security_manager`- og dekoratorstubber for rate limiting/IP-kontroll, men ikke en ferdig verifisert DDoS-beskyttelse.
- Verifiser at klientens opprinnelige JWT blir bundet til den autoritative WebSocket-tilkoblingen, ikke at hver forespørsel selv kan definere hvilken økt som er aktiv.

## Anbefalt validering

1. Få `server3` til å **kompilere og starte** i et isolert utviklingsmiljø.
2. Lag automatiske tester for registrering, innlogging, ugyldige token, socket-lukking og timeout.
3. Test DM-levering med begge online, én offline, ulike aktive rom og databasefeil.
4. Test hver action i `config.json` mot faktisk eksisterende handler og rett sync/async-kall.
5. Dokumenter PostgreSQL DDL/migrasjoner og legg til CI for linting, statiske kontroller og tester.

> Dette dokumentet gir ingen garanti for at en action fungerer i praksis. Det beskriver kildekodens hensikt, observert flyt og konkrete avvik.
