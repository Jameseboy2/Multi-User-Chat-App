import socket
import threading

# --- Configuration ---
HOST = '127.0.0.1'  # Localhost
PORT = 5555         # Arbitrary non-privileged port

# List to keep track of all connected client sockets
active_clients = []

def broadcast(message, sender_socket):
    """
    Sends a message to all connected clients except the one who sent it.
    """
    for client in active_clients:
        if client != sender_socket:
            try:
                client.send(message)
            except Exception as e:
                # If sending fails, we assume the client disconnected gracefully or ungracefully
                print(f"[ERROR] Failed to send message to a client: {e}")
                remove_client(client)

def remove_client(client_socket):
    """
    Safely removes a client from the active list and closes their connection.
    """
    if client_socket in active_clients:
        active_clients.remove(client_socket)
        client_socket.close()

def handle_client(client_socket, client_address):
    """
    Runs in a separate thread for each connected client.
    Listens for incoming messages and broadcasts them.
    """
    print(f"[NEW CONNECTION] {client_address} connected.")
    
    while True:
        try:
            # Receive data from the client (up to 1024 bytes)
            message = client_socket.recv(1024)
            
            # If recv() returns an empty byte string, the client disconnected gracefully
            if not message:
                break
                
            # Broadcast the valid message to everyone else
            broadcast(message, client_socket)
            
        except ConnectionResetError:
            # Handles abrupt disconnections (e.g., the client closed their terminal)
            print(f"[DISCONNECTED] {client_address} abruptly disconnected.")
            break
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred with {client_address}: {e}")
            break
            
    # Cleanup when the loop breaks (client disconnected)
    remove_client(client_socket)
    print(f"[CONNECTION CLOSED] {client_address} left the chat.")

def start_server():
    """
    Initializes the server socket and listens for incoming connections.
    """
    # 1. socket(): Create a new socket. 
    # AF_INET specifies the IPv4 address family.
    # SOCK_STREAM specifies that this is a TCP socket.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Optional but recommended: Allow the server to reuse the address immediately after restarting
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # 2. bind(): Associate the socket with a specific network interface (IP) and port number.
    server_socket.bind((HOST, PORT))

    # 3. listen(): Put the socket into listening mode to accept incoming connection requests.
    server_socket.listen()
    print(f"[STARTING] Server is listening on {HOST}:{PORT}...")

    while True:
        # 4. accept(): Wait for a client to connect. This blocks execution until a connection arrives.
        # It returns a NEW socket object specifically for this client, and their address (IP, Port).
        client_socket, client_address = server_socket.accept()
        
        # Add the new client to our active list
        active_clients.append(client_socket)
        
        # Create and start a new thread to handle this specific client
        thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

if __name__ == "__main__":
    start_server()