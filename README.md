# super-server
# Server 2
-----Server------
Aws based cloud server using EC2
run run_aws to access the aws server
activate the env: source myenv/bin/avtivate
open the git reppo: cd Server-project
to run the server: python3 server2/server_manager.py

----specifics----
token based authetentication
https with own domain
can handle a lot of users, scaleable by design
role permission system
user profiles
createable groupchats
friends


WIP:
    E2EE
    DDOS prevention

----client-----
App connected to the server, connects automatically you need to register a user for access.
a communication platform
Can send messages global, to specific users or in groups.






# Server 1
# LAB
Når du kjører klienten og servern er på, for å koble til skriv connect.

------SERVER---------

server funksjoner:

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


vær forsiktig når du lager funksjoner, du må sørge for selv at de opprettholder sikkerhet og tilgangsnivå


NOTER! set_user er den eneste ikke trygge funskjonen enn så lenge, klienten kan lage egen klient kode og overfylle minne til serveren 
med session profiler

fix: 

    cooldown på funskjonen

    serveren aktivt sjekker gjevnlig over sessionprofiler etter sockets som ikke funker

    server generer en unique token som varer kunn i et par minutter som bare genneres når en socket har en connection

    grense på antall session profiler

    sjekker om brukern er registrert siden servern forventer verifisering først uansett

create_user lar deg lage bruker utenomvidere, stor svakhet siden en bruker kan lage uendelige brukere

fix:

    En bruker per telefon nummer

    En bruker per email

    id innloggin



-----------KLIENT-----------

Kommandoer:

    exit: når logget in disconnecter klienten


Alle meldinger du vil sende til serveren MÅ generes fra gen_message

alle meldinger SKAL inkludere en tag og action der action er funskjonen du will spørre om å kjøre
