# LAB
Når du kjører klienten og servern er på, for å koble til skriv connect.

------SERVER---------

server funksjoner
  "veus": "verify_user",
        "ping": "ping", 0 inputs, kan skrive ping i klienten for å få pong tilbake
        "set_user": "set_client",
        "kill_server": "kill_server", 1 input
        "create_user": "create_user",
        "change_permission_level": "change_persmission_level", input 1: bruker, input 2: nivå
        "show_online_users": "show_online_users", 0 inputs
        "message_user": "message_user" input 1: bruker, input 2: melding


for å kjøre funksjoner fra klienten referer til overnfor

Steg for å lafe ny server funksjon, eksempel:

alle funskjoner skal ha en parameter for input selvom funskjonen ikke bruker den
om funskjonen har inputs er det første param, inputs kommer alltid som en liste!
def change_persmission_level(data, token): eksempel på hvordan håndtere input data
    try: #checks if data is given in the right way
        target_user = data[0]
        new_access_level = data[1]

def eksempel(msg, token): #vis funksjonen dealer med noe med klienter å gjøre, inkludere token!!
    payload = get_user_profile(token) kall på get_user_profile med token, den returner session profiler og verifiserer payload. Kan evt bruke server_utils og verifisere manuelt og hente session key for mer kontrol
    if payload:
       gjør noe her
    else:
        return "invalid token" alle returns fra funskjoner requested fra klienter blir sendt til klienten og den vil printes om det ikke er noe midtveis feil


KLIENT

Kommandoer:
exit: når logget in disconnecter klienten