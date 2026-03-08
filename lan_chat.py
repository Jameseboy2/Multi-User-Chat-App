import socket
import threading
import sys
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext

# --- Configuration ---
TCP_PORT = 5555
UDP_PORT = 5556
DISCOVERY_MSG = b"LOOKING_FOR_HOST"

class LancChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LAN Chat Pro")
        self.root.geometry("450x550")
        self.root.resizable(False, False)
        
        # Network State Variables
        self.client_socket = None
        self.server_socket = None
        self.udp_socket = None
        self.active_clients = []
        self.is_hosting = False
        self.username = ""
        
        # Start at the main menu
        self.current_frame = None
        self.show_main_menu()

    def clear_window(self):
        """Destroys all widgets in the current window to load a new screen."""
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = tk.Frame(self.root, padx=20, pady=20)
        self.current_frame.pack(expand=True, fill="both")

    # ==========================================
    # UI SCREENS (Navigation)
    # ==========================================

    def show_main_menu(self):
        """Displays the starting menu."""
        self.clear_window()
        self.cleanup_network() # Ensure all connections are closed when returning here
        
        tk.Label(self.current_frame, text="LAN Chat", font=("Helvetica", 24, "bold")).pack(pady=40)
        
        tk.Button(self.current_frame, text="Host a Chat Room", width=25, height=2, 
                  command=self.show_host_menu).pack(pady=10)
        tk.Button(self.current_frame, text="Join a Chat Room", width=25, height=2, 
                  command=self.show_join_menu).pack(pady=10)
        tk.Button(self.current_frame, text="Quit", width=25, height=2, 
                  command=self.root.quit).pack(pady=10)

    def show_host_menu(self):
        """Displays the setup screen for hosting."""
        self.clear_window()
        
        tk.Label(self.current_frame, text="Host a Room", font=("Helvetica", 18)).pack(pady=20)
        
        tk.Label(self.current_frame, text="Room Name:").pack()
        self.room_entry = tk.Entry(self.current_frame, width=30)
        self.room_entry.pack(pady=5)
        
        tk.Label(self.current_frame, text="Your Username:").pack()
        self.host_name_entry = tk.Entry(self.current_frame, width=30)
        self.host_name_entry.pack(pady=5)
        
        tk.Button(self.current_frame, text="Start Hosting", bg="lightblue", width=20, 
                  command=self.start_hosting).pack(pady=20)
        tk.Button(self.current_frame, text="Go Back", width=20, 
                  command=self.show_main_menu).pack()

    def show_join_menu(self):
        """Displays the server browser to join existing rooms."""
        self.clear_window()
        
        tk.Label(self.current_frame, text="Join a Room", font=("Helvetica", 18)).pack(pady=10)
        
        # Listbox to display available servers
        self.host_listbox = tk.Listbox(self.current_frame, width=40, height=8)
        self.host_listbox.pack(pady=5)
        
        # Refresh Button
        self.refresh_btn = tk.Button(self.current_frame, text="Refresh List", 
                                     command=self.trigger_refresh)
        self.refresh_btn.pack(pady=5)
        
        tk.Label(self.current_frame, text="Your Username:").pack(pady=(10,0))
        self.join_name_entry = tk.Entry(self.current_frame, width=30)
        self.join_name_entry.pack(pady=5)
        
        tk.Button(self.current_frame, text="Join Selected Room", bg="lightgreen", width=20, 
                  command=self.join_selected_room).pack(pady=15)
        tk.Button(self.current_frame, text="Go Back", width=20, 
                  command=self.show_main_menu).pack()
        
        # Auto-scan when opening this menu
        self.trigger_refresh()

    def show_chat_screen(self):
        """Displays the actual chat interface."""
        self.clear_window()
        
        # ScrolledText is a text box with a built-in scrollbar
        self.chat_display = scrolledtext.ScrolledText(self.current_frame, wrap=tk.WORD, width=50, height=20, state='disabled')
        self.chat_display.pack(pady=10)
        
        # Input area
        bottom_frame = tk.Frame(self.current_frame)
        bottom_frame.pack(fill="x")
        
        self.msg_entry = tk.Entry(bottom_frame, width=35)
        self.msg_entry.pack(side="left", padx=(0, 10))
        # Bind the Enter key to send messages too!
        self.msg_entry.bind("<Return>", lambda event: self.send_message())
        
        tk.Button(bottom_frame, text="Send", command=self.send_message).pack(side="left")
        
        tk.Button(self.current_frame, text="Disconnect & Go Back", width=20, fg="red",
                  command=self.show_main_menu).pack(pady=15)

    # ==========================================
    # NETWORK LOGIC & THREADING
    # ==========================================

    def start_hosting(self):
        room_name = self.room_entry.get().strip()
        username = self.host_name_entry.get().strip()
        
        # Error handling for bad inputs
        if not room_name or not username:
            messagebox.showwarning("Invalid Input", "Room Name and Username cannot be empty!")
            return
            
        self.username = username
        self.is_hosting = True
        
        # Start Server threads
        threading.Thread(target=self.tcp_server_thread, daemon=True).start()
        threading.Thread(target=self.udp_discovery_responder, args=(room_name,), daemon=True).start()
        
        time.sleep(0.2) # Brief pause to let server bind
        self.connect_to_server('127.0.0.1')

    def trigger_refresh(self):
        """Starts the scanning thread and disables the button temporarily."""
        self.refresh_btn.config(state="disabled", text="Scanning...")
        self.host_listbox.delete(0, tk.END) # Clear current list
        self.discovered_hosts = [] 
        
        # Run scan in background so GUI doesn't freeze
        threading.Thread(target=self.scan_for_hosts_thread, daemon=True).start()

    def scan_for_hosts_thread(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_socket.settimeout(2.0)
        
        try:
            udp_socket.sendto(DISCOVERY_MSG, ('<broadcast>', UDP_PORT))
            while True:
                data, addr = udp_socket.recvfrom(1024)
                msg = data.decode('utf-8')
                if msg.startswith("HOST_HERE|"):
                    host_name = msg.split('|')[1]
                    host_info = (host_name, addr[0])
                    if host_info not in self.discovered_hosts:
                        self.discovered_hosts.append(host_info)
                        # Safely update GUI from background thread
                        self.root.after(0, self.host_listbox.insert, tk.END, f"{host_name} ({addr[0]})")
        except socket.timeout:
            pass
        finally:
            udp_socket.close()
            # Safely re-enable the button via the main thread
            self.root.after(0, lambda: self.refresh_btn.config(state="normal", text="Refresh List"))

    def join_selected_room(self):
        selection = self.host_listbox.curselection()
        username = self.join_name_entry.get().strip()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select a room from the list!")
            return
        if not username:
            messagebox.showwarning("Invalid Input", "Please enter a username!")
            return
            
        self.username = username
        selected_index = selection[0]
        server_ip = self.discovered_hosts[selected_index][1]
        
        self.connect_to_server(server_ip)

    def connect_to_server(self, ip):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((ip, TCP_PORT))
            self.show_chat_screen()
            self.display_text(f"Connected as {self.username}!\n", "system")
            
            # Start listening for messages
            threading.Thread(target=self.receive_messages_thread, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect: {e}")

    # ==========================================
    # CHAT & SERVER BACKEND
    # ==========================================

    def send_message(self):
        msg = self.msg_entry.get().strip()
        if msg and self.client_socket:
            formatted_msg = f"[{self.username}]: {msg}"
            try:
                self.client_socket.send(formatted_msg.encode('utf-8'))
                self.display_text(f"{formatted_msg}\n")
                self.msg_entry.delete(0, tk.END) # Clear input box
            except:
                messagebox.showerror("Error", "Lost connection to server.")

    def receive_messages_thread(self):
        while self.client_socket:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if not message:
                    break
                self.display_text(f"{message}\n")
            except:
                break
        self.display_text("[Disconnected from server]\n", "system")

    def display_text(self, text, tag=None):
        """Helper to safely insert text into the disabled chat display."""
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, text)
        self.chat_display.see(tk.END) # Auto-scroll to bottom
        self.chat_display.config(state='disabled')

    def tcp_server_thread(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', TCP_PORT))
        self.server_socket.listen()

        while self.is_hosting:
            try:
                client_sock, _ = self.server_socket.accept()
                self.active_clients.append(client_sock)
                threading.Thread(target=self.handle_client_thread, args=(client_sock,), daemon=True).start()
            except:
                break

    def handle_client_thread(self, client_socket):
        while self.is_hosting:
            try:
                message = client_socket.recv(1024)
                if not message: break
                # Broadcast
                for c in self.active_clients:
                    if c != client_socket:
                        try: c.send(message)
                        except: pass
            except: break
        if client_socket in self.active_clients:
            self.active_clients.remove(client_socket)
        client_socket.close()

    def udp_discovery_responder(self, room_name):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.bind(('', UDP_PORT))
        
        while self.is_hosting:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                if data == DISCOVERY_MSG:
                    self.udp_socket.sendto(f"HOST_HERE|{room_name}".encode('utf-8'), addr)
            except:
                break

    def cleanup_network(self):
        """Closes sockets when navigating back to the main menu."""
        self.is_hosting = False
        if self.client_socket:
            try: self.client_socket.close()
            except: pass
            self.client_socket = None
            
        if self.server_socket:
            try: self.server_socket.close()
            except: pass
            self.server_socket = None
            
        if self.udp_socket:
            try: self.udp_socket.close()
            except: pass
            self.udp_socket = None
        self.active_clients.clear()

if __name__ == "__main__":
    root = tk.Tk()
    app = LancChatApp(root)
    root.mainloop() # This starts the GUI event loop!