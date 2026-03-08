import socket
import threading
import sys

# --- Configuration ---
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5555

def receive_messages(client_socket):
    """
    Continuously listens for messages coming from the server.
    """
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if not message:
                # Server closed the connection
                print("\n[DISCONNECTED] Disconnected from the server.")
                break
            
            # Print the received message to the console
            # '\r' helps clear the current input line so incoming messages 
            # don't mess up what the user is currently typing.
            print(f"\r{message}\n", end="")
            
        except ConnectionResetError:
            print("\n[ERROR] Connection to the server was lost.")
            break
        except Exception as e:
            print(f"\n[ERROR] An error occurred: {e}")
            break
            
    # If the loop breaks, exit the program
    client_socket.close()
    sys.exit()

def start_client():
    """
    Initializes the client, connects to the server, and manages threads.
    """
    username = input("Enter your username to join the chat: ")
    
    # 1. socket(): Create the client TCP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # 2. connect(): Attempt to connect to the server's IP and Port
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        print(f"[CONNECTED] Connected to the server as '{username}'. You can start typing!")
    except Exception as e:
        print(f"[ERROR] Unable to connect to the server: {e}")
        return

    # Start a background thread to listen for incoming messages
    receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
    # Making it a daemon thread ensures it closes automatically when the main program exits
    receive_thread.daemon = True 
    receive_thread.start()

    # Main thread: continuously wait for user input and send messages
    while True:
        try:
            # Wait for user input
            message_content = input()
            
            # Prevent sending empty messages
            if message_content.strip():
                # Format the message exactly as requested: [Username]: Message content
                formatted_message = f"[{username}]: {message_content}"
                
                # Send the encoded message to the server
                client_socket.send(formatted_message.encode('utf-8'))
                
        except KeyboardInterrupt:
            # Handles the user pressing Ctrl+C gracefully
            print("\n[EXIT] Leaving the chat...")
            client_socket.close()
            break

if __name__ == "__main__":
    start_client()