from client.loads import *
import ast
import queue
import client.datastructures as ds
from client.thread_manager import *
from  client.client_utils import *

HOST = "localhost"  # The server's hostname or IP address
PORT = 12345  # The port used by the server

run_terminal = True
HEARTBEAT_INTERVAL = 3
short_lived_client = True

server_response_log = []
receieve_queue = { #tag associated with where message has associated function
    "heartbeat":     queue.Queue(),
    "join_protocol": queue.Queue(),
    "main":          queue.Queue(),
    "chat":          queue.Queue(),
    "status_check":  queue.Queue()
}

chat_data = {
    "path": None,
    "chat": None
}

signals = {
}

heartbeat_functions = {}

def send_to_server(client_sock, msg, supress = False):
    if type(msg) is dict:
        try:
            client_sock.sendall(json.dumps(msg).encode())
            return True
        except Exception as e:
            if not supress:
                print(f"Could not send message to server {e}\n")
        except socket.timeout:
            print("Timed out trying to send message")
    else:
        if not supress:
            print("Invalid message format, please send as dictionary")

def recieve_from_server(client_sock, wait_for=2, expected_tag=None, supress=False, no_status_check=False, origin=False):
    client_sock.settimeout(wait_for)
    try:
        data = client_sock.recv(1024)
    except Exception as e:
        if not no_status_check:
            add_to_response_log(None)
        if not supress:
            print(f"Could not recieve from server: {e} | {origin}\n")
        return None
    except socket.timeout():
        if not no_status_check:
            add_to_response_log(None)
        if not supress:
             print(f"Timed out trying to receieve from server| {origin}")
        return None
    
    buffer = data.decode()
    while "\n" in buffer:
        message, buffer = buffer.split("\n", 1)

        msg = json.loads(message)
        content = msg["data"][0]
        tag = msg["data"][1]
        add_to_response_log(content)

        if tag in receieve_queue:
            receieve_queue[tag].put(content)
            for match in signals:
                if match == tag:
                    signals[tag].emit(content)
        else:
            print(f"invalid tag {tag} {content}")
            return False
        
        return True

def new_user_protocol(client_sock, user, password, token):
    message = gen_message("create_user", {"username": user, "password": password, "token": token}, "join_protocol")
    send_to_server(client_sock, message)
    response = receieve_queue["join_protocol"].get(timeout=1)

    if response:
        if response == "1":
            message = {"user": user, "socket": str(client_sock), "token": token}
            msg = gen_message("set_user", message , "join_protocol")
            send_to_server(client_sock, msg)
            success = receieve_queue["join_protocol"].get(timeout=1)
            if success:
                print(f"Welcome {user}")
                config["username"] = user
                config["successfull_login"] = True
                config["activate_heartbeat"] = True
                config["register_attempts"] = 0
                return 1
            else:
                print("Could not set up server profile, profile may already be setup or failed to receive token")
                return False
        else:
            print("\nUser already exists\n")

    else:
        print("Did not receieve from server or some unexpected error happebned")
        return False

def gen_message(action="", data="", tag="", token=None):
    return {"action": action, "data":data, "tag": tag, "token": token}

def add_to_response_log(response):
    log_len = len(server_response_log)
    if log_len < 5:
        server_response_log.append(response)
    else:
        server_response_log.pop(0)
        server_response_log.append(response)

def client_joined(client_sock, user, password, token):
    message = gen_message("veus", {"username": user, "password": password, "token": token}, "join_protocol")
    send_to_server(client_sock, message)
    try:
        response = receieve_queue["join_protocol"].get(timeout=1)
    except Exception as e:
        return False
    
    if response:    
        if response == "1":
            message = {"user": user, "socket": str(client_sock), "token": token}
            msg = gen_message("set_user", message , "join_protocol")
            send_to_server(client_sock, msg)
            try:
                success = receieve_queue["join_protocol"].get(timeout=1)

            except Exception as e:
                return False  
   
            if success != "False" :
                print(f"Welcome back {user}")
                config["username"] = user
                config["successfull_login"] = True
                config["login_attempts"] = 0
                return 1
            else:
                print("Could not set up server profile, profile may already be setup or failed to receive token")
                return False
        elif response == "2":
            print("\n Client is already logged in, please logout before attempting to login with another user.")
            return 2
        else:
            print("\nIncorrect username or password\n")
            return False

    else:
        print("Did not receieve from server or some unexpected error happebned")
        return False

def status_check(client_socket, token, force_ping = False):
    for response in server_response_log:
        if response == "disconnect":
            print("Warning: server disconnected client")
            return False
        
        if response == None or force_ping == True: #ping server
            for i in range(3):
                msg = gen_message("ping", "", "status_check", token)
                connection = send_to_server(client_socket, msg, True)
                if connection:
                    response = receieve_queue["status_check"].get(timeout=1)
                    if response:
                        return True
                
                time.sleep(0.05)
            print("Could not ping server, no connection to server")
            return False
    
    return True
    #ping

def async_heartbeat(client_socket, stop, token):
    try:
        msg = gen_message("ping", "", "heartbeat", token)
        sent = send_to_server(client_socket, msg, True) 
    except Exception as e:
        print(f"Error at requesting ping from heartbeat {e}, sent: {sent}")
        return
    
    try:
        recieved = receieve_queue["heartbeat"].get(timeout=1)
        if not recieved:
            return False
        return recieved
    
    except queue.Empty:
        pass
            
def heartbeat(client_socket, stop, token):
    """heartbeat function with a blocking function"""
    itr_count = 5
    count = 0
    while not stop.is_set():
        if not stop.is_set() or config["stop"] == True:
            time.sleep(HEARTBEAT_INTERVAL/itr_count)
            count += 1
            if  count >= itr_count:
                count = 0
                recieved = False
                try:
                    for func_key in heartbeat_functions:
                        heartbeat_functions[func_key]()

                except Exception as e:
                    print(f"Error at heartbeat function {e} \n{func_key}")

                try:
                    recieved = async_heartbeat(client_socket, stop, token)

                    if not recieved:
                        print("Heartbeat fail")
                        print(f"recieved {recieved}")
                        status = status_check(client_socket, token, True)

                except Exception as e:
                    print(f"Heartbeat: {e}")

    print("closing heartbeat")
                 
def async_receive_thread(client_sock, stop):
    counter = 0
    while not stop.is_set():
        try:
            recieve_from_server(client_sock, 1, None, True, True)
            counter = 0
        except Exception as e:
            counter += 1
            if counter >= 10:
                connected = status_check(client_sock, config["token"])
                if not connected:
                    print(f"Error recieving with server, bad connection or server is down. {e}")
                    print("\n closing client")
                    stop.set()
                    return
                else:
                    counter = 0
        
        time.sleep(0.1)
    print("recieve ended")

def receive_thread(client_socket, stop):
    """cheesy solution to do async and threading"""
    async_receive_thread(client_socket, stop)
    
def run_client(client_sock, heartbeat_stop):
    connected = True

    while connected:

        if heartbeat_stop.is_set() or config["stop"] == True:
            connected = False
            return

        if config["successfull_login"]:   
            try:
                recieved = receieve_queue["main"].get(timeout=1)
                if not recieved:
                    continue

            except queue.Empty:
                continue

            except Exception as e:
                print(f"{e}")
                return
            
            try:
                recieved = ast.literal_eval(recieved)
            except:
                continue

            if recieved:
                if recieved["signal"] in signals:
                    signals[recieved["signal"]].emit(recieved["data"])

        time.sleep(0.25)
