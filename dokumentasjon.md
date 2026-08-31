Every thread or courotine created must go thru the thread manager

"""
KOMMUNIKASJONSFLYT — kort oversikt
===================================
1. cross_comminication_queues:  GUI -> klient-tråd (utgående forespørsler)
2. receieve_events/receieve_queue: server -> intern dispatch, nøkkel = "tag" i meldingen
3. signals (client.signals):    intern dispatch -> Qt GUI-tråd (trådsikker levering)
4. full_pull_queue(tag):        tømmer receieve_queue[tag] og emit'er matchende Qt-signal

POLLING I run_client_mainloop:
- "chat" pollest hver runde (prioritert, høy frekvens)
- "main" pollest kun når receieve_events["main"] er satt (unngår unødvendig flooding)
- Alle andre tags (join_protocol, start_login, start_register, set_login_info,
  set_register_info, status_check) hører til oppstartsprotokollen og pollest
  KUN i run_init/run_login, ikke i mainloopen.
- status_check: mulig deprecated - verifiser bruk før du bygger videre på den.

LEGGE TIL NYTT EVENT:
1. register_tag("mitt_navn")                                  [klientside]
2. connect_signal("mitt_navn", self.min_slot, dict)            [GUI-side, i widget __init__]
3. Server må sende {"signal": "mitt_navn", "data": {...}} med matchende tag
4. Hvis tag skal pollest live (ikke bare ved event) -> legg inn i run_client_mainloop
   sin polling-logikk manuelt (kun chat/main gjør dette per design)
"""