import socket
import asyncio

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 12345  # The port used by the server

short_lived_client = True


async def client(id):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock:
        loop = asyncio.get_event_loop()
        client_sock.setblocking(False)
        try:
            await loop.sock_connect(client_sock, (HOST, PORT))
            print(f"Client {id} connected.\n")
        except Exception as e:
            print(f"Client {id} did not connect: {e}\n")
            
        if not short_lived_client:
            client_inp = await input("Input to server: ")
            print("\n")
        else:
            try:
                await loop.sock_sendall(client_sock, str(id).encode())
            except Exception as e:
                print(f"Could not send message to server {e}\n")
            
            try:
                data = await loop.sock_recv(client_sock, 1024)
                print(data.decode())
            except Exception as e:
                print(f"Could not recieve from server: {e}\n")
  
            client_sock.close()
            print(f"Disconnected client {id}\n")

#run
async def main():
    num_clients = 5
    tasks = [client(i) for i in range(num_clients)]
    await asyncio.gather(*tasks)

asyncio.run(main())

