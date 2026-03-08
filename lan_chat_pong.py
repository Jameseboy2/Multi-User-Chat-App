import socket
import threading
import sys
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext
import json
import urllib.request

# --- Configuration ---
TCP_PORT = 5555
UDP_PORT = 5556
DISCOVERY_MSG = b"LOOKING_FOR_HOST"
GAME_TICK_RATE = 0.03  

class LancChatPongApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LAN Chat & Pong Pro")
        self.root.geometry("800x800") 
        self.root.resizable(False, False)
        
        self.client_socket = None
        self.server_socket = None
        self.udp_socket = None
        self.is_hosting = False
        self.username = ""
        self.active_keys = set() 
        
        self.active_clients = {} 
        self.player_queue = []   
        self.game_state = {
            "p1_y": 160, "p2_y": 160, 
            "b_x": 380, "b_y": 200, 
            "b_dx": 6, "b_dy": 6,
            "s1": 0, "s2": 0,
            "p1_name": "Waiting...", "p2_name": "Waiting...",
            "p1_ready": False, "p2_ready": False
        }
        
        self.p1_up = False; self.p1_down = False
        self.p2_up = False; self.p2_down = False
        self.game_active = False

        self.current_frame = None
        self.show_main_menu()

    def clear_window(self):
        if self.current_frame: self.current_frame.destroy()
        self.current_frame = tk.Frame(self.root, padx=20, pady=20)
        self.current_frame.pack(expand=True, fill="both")

    # ==========================================
    # UI SCREENS
    # ==========================================

    def show_main_menu(self):
        self.clear_window()
        self.cleanup_network()
        tk.Label(self.current_frame, text="Pong & Chat", font=("Helvetica", 24, "bold")).pack(pady=40)
        tk.Button(self.current_frame, text="Host a Room", width=25, height=2, command=self.show_host_menu).pack(pady=10)
        tk.Button(self.current_frame, text="Join a Room", width=25, height=2, command=self.show_join_menu).pack(pady=10)
        tk.Button(self.current_frame, text="Quit", width=25, height=2, command=self.root.quit).pack(pady=10)

    def show_host_menu(self):
        self.clear_window()
        tk.Label(self.current_frame, text="Host a Room", font=("Helvetica", 18)).pack(pady=20)
        tk.Label(self.current_frame, text="Room Name:").pack()
        self.room_entry = tk.Entry(self.current_frame, width=30)
        self.room_entry.pack(pady=5)
        tk.Label(self.current_frame, text="Your Username:").pack()
        self.host_name_entry = tk.Entry(self.current_frame, width=30)
        self.host_name_entry.pack(pady=5)
        tk.Button(self.current_frame, text="Start Hosting", bg="lightblue", width=20, command=self.start_hosting).pack(pady=20)
        tk.Button(self.current_frame, text="Go Back", width=20, command=self.show_main_menu).pack()

    def show_join_menu(self):
        self.clear_window()
        tk.Label(self.current_frame, text="Join a Room", font=("Helvetica", 18)).pack(pady=5)
        
        tk.Label(self.current_frame, text="Your Username (Required for both methods):").pack(pady=(5,0))
        self.join_name_entry = tk.Entry(self.current_frame, width=30)
        self.join_name_entry.pack(pady=5)

        tk.Label(self.current_frame, text="--- Local Network (LAN) ---", fg="gray").pack(pady=(15, 5))
        self.host_listbox = tk.Listbox(self.current_frame, width=40, height=5)
        self.host_listbox.pack(pady=5)
        
        btn_frame = tk.Frame(self.current_frame)
        btn_frame.pack(pady=5)
        self.refresh_btn = tk.Button(btn_frame, text="Refresh List", command=self.trigger_refresh)
        self.refresh_btn.pack(side="left", padx=5)
        tk.Button(btn_frame, text="Join LAN Room", bg="lightgreen", command=self.join_selected_room).pack(side="left", padx=5)

        tk.Label(self.current_frame, text="--- Internet Connect (WAN) ---", fg="gray").pack(pady=(20, 5))
        tk.Label(self.current_frame, text="Enter Host's Public IP Address:").pack()
        self.manual_ip_entry = tk.Entry(self.current_frame, width=30)
        self.manual_ip_entry.pack(pady=5)
        
        tk.Button(self.current_frame, text="Direct Connect", bg="lightblue", width=20, command=self.join_direct_ip).pack(pady=5)
        tk.Button(self.current_frame, text="Go Back", width=20, command=self.show_main_menu).pack(pady=20)
        
        self.trigger_refresh()

    def show_game_screen(self):
        self.clear_window()
        self.canvas = tk.Canvas(self.current_frame, width=760, height=400, bg="black")
        self.canvas.pack(pady=5)
        
        self.paddle1 = self.canvas.create_rectangle(30, 160, 45, 240, fill="white")
        self.paddle2 = self.canvas.create_rectangle(715, 160, 730, 240, fill="white")
        self.ball = self.canvas.create_oval(370, 190, 390, 210, fill="white")
        
        self.score_text = self.canvas.create_text(380, 30, text="0 - 0", fill="white", font=("Arial", 20, "bold"))
        self.p1_text = self.canvas.create_text(150, 30, text="P1", fill="white", font=("Arial", 12))
        self.p2_text = self.canvas.create_text(610, 30, text="P2", fill="white", font=("Arial", 12))
        self.status_text = self.canvas.create_text(380, 100, text="", fill="yellow", font=("Arial", 14))

        controls_frame = tk.Frame(self.current_frame)
        controls_frame.pack(pady=5)
        
        tk.Button(controls_frame, text="Join Game Queue", bg="orange", command=self.send_join_queue).pack(side="left", padx=10)
        tk.Button(controls_frame, text="Ready Up", bg="lightgreen", command=self.send_ready).pack(side="left", padx=10)

        self.chat_display = scrolledtext.ScrolledText(self.current_frame, wrap=tk.WORD, width=80, height=10, state='disabled')
        self.chat_display.pack(pady=5)
        
        bottom_frame = tk.Frame(self.current_frame)
        bottom_frame.pack(fill="x")
        self.msg_entry = tk.Entry(bottom_frame, width=65)
        self.msg_entry.pack(side="left", padx=(0, 10))
        self.msg_entry.bind("<Return>", lambda e: self.send_chat())
        tk.Button(bottom_frame, text="Send Chat", command=self.send_chat).pack(side="left")
        
        tk.Button(self.current_frame, text="Disconnect", fg="red", command=self.show_main_menu).pack(pady=10)
        
        self.root.bind("<KeyPress-Up>", self.on_key_press)
        self.root.bind("<KeyPress-Down>", self.on_key_press)
        self.root.bind("<KeyRelease-Up>", self.on_key_release)
        self.root.bind("<KeyRelease-Down>", self.on_key_release)

    # ==========================================
    # INPUT & NETWORK LOGIC (Client)
    # ==========================================

    def on_key_press(self, event):
        if event.keysym not in self.active_keys:
            self.active_keys.add(event.keysym)
            self.send_network_message({"type": "INPUT", "key": event.keysym, "pressed": True})

    def on_key_release(self, event):
        if event.keysym in self.active_keys:
            self.active_keys.remove(event.keysym)
            self.send_network_message({"type": "INPUT", "key": event.keysym, "pressed": False})

    def send_join_queue(self):
        self.send_network_message({"type": "JOIN_QUEUE"})

    def send_ready(self):
        self.send_network_message({"type": "READY"})

    def start_hosting(self):
        room = self.room_entry.get().strip(); user = self.host_name_entry.get().strip()
        if not room or not user: return
        self.username = user; self.is_hosting = True
        
        threading.Thread(target=self.tcp_server_thread, daemon=True).start()
        threading.Thread(target=self.udp_discovery_responder, args=(room,), daemon=True).start()
        threading.Thread(target=self.server_game_loop, daemon=True).start()
        
        time.sleep(0.2)
        self.connect_to_server('127.0.0.1')
        
        # NEW: Fetch IP in the background right after hosting starts
        threading.Thread(target=self.fetch_public_ip, daemon=True).start()

    def fetch_public_ip(self):
        """NEW: Automatically grabs the host's public IP to share."""
        try:
            # We use api.ipify.org, a simple service that just returns your IP
            ip = urllib.request.urlopen('https://api.ipify.org', timeout=5).read().decode('utf8')
            # Add a slight delay to ensure the client is fully connected before sending chat
            time.sleep(1)
            self.send_network_message({"type": "CHAT", "msg": f"[SYSTEM]: Your Public IP for internet friends is: {ip}"})
        except Exception:
            time.sleep(1)
            self.send_network_message({"type": "CHAT", "msg": "[SYSTEM]: Could not automatically fetch Public IP."})

    def trigger_refresh(self):
        self.refresh_btn.config(state="disabled", text="Scanning...")
        self.host_listbox.delete(0, tk.END); self.discovered_hosts = [] 
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
                    info = (msg.split('|')[1], addr[0])
                    if info not in self.discovered_hosts:
                        self.discovered_hosts.append(info)
                        self.root.after(0, self.host_listbox.insert, tk.END, f"{info[0]} ({addr[0]})")
        except: pass
        finally:
            udp_socket.close()
            self.root.after(0, lambda: self.refresh_btn.config(state="normal", text="Refresh List"))

    def join_selected_room(self):
        selection = self.host_listbox.curselection()
        user = self.join_name_entry.get().strip()
        if not user:
            messagebox.showwarning("Invalid Input", "Please enter a username!")
            return
        if not selection:
            messagebox.showwarning("No Selection", "Please select a LAN room from the list!")
            return
        self.username = user
        self.connect_to_server(self.discovered_hosts[selection[0]][1])

    def join_direct_ip(self):
        target_ip = self.manual_ip_entry.get().strip()
        user = self.join_name_entry.get().strip()
        if not user:
            messagebox.showwarning("Invalid Input", "Please enter a username!")
            return
        if not target_ip:
            messagebox.showwarning("Invalid Input", "Please enter an IP address!")
            return
        self.username = user
        self.connect_to_server(target_ip)

    def connect_to_server(self, ip):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((ip, TCP_PORT))
            self.show_game_screen()
            self.send_network_message({"type": "JOIN", "name": self.username})
            threading.Thread(target=self.receive_messages_thread, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed. Ensure the IP is correct and the host has Port Forwarding enabled.\nDetails: {e}")

    def send_network_message(self, data_dict):
        if self.client_socket:
            try:
                msg = json.dumps(data_dict) + "\n"
                self.client_socket.send(msg.encode('utf-8'))
            except: pass

    def send_chat(self):
        msg = self.msg_entry.get().strip()
        if msg:
            self.send_network_message({"type": "CHAT", "msg": msg})
            self.msg_entry.delete(0, tk.END)

    def receive_messages_thread(self):
        buffer = ""
        while self.client_socket:
            try:
                data = self.client_socket.recv(4096).decode('utf-8')
                if not data: break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        packet = json.loads(line)
                        if packet["type"] == "CHAT":
                            self.root.after(0, self.display_text, f"{packet['msg']}\n")
                        elif packet["type"] == "STATE":
                            self.root.after(0, self.update_canvas, packet)
            except: break
        self.root.after(0, self.display_text, "[Disconnected]\n")

    def display_text(self, text):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, text)
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')

    def update_canvas(self, state):
        self.canvas.coords(self.paddle1, 30, state["p1_y"], 45, state["p1_y"] + 80)
        self.canvas.coords(self.paddle2, 715, state["p2_y"], 730, state["p2_y"] + 80)
        self.canvas.coords(self.ball, state["b_x"]-10, state["b_y"]-10, state["b_x"]+10, state["b_y"]+10)
        self.canvas.itemconfig(self.score_text, text=f"{state['s1']} - {state['s2']}")
        
        p1_status = f"P1: {state['p1_name']} " + ("(READY)" if state["p1_ready"] else "(Not Ready)")
        self.canvas.itemconfig(self.p1_text, text=p1_status)
        
        p2_status = f"P2: {state['p2_name']} " + ("(READY)" if state["p2_ready"] else "(Not Ready)")
        if state['q_len'] > 0: p2_status += f"\n(+{state['q_len']} in queue)"
        self.canvas.itemconfig(self.p2_text, text=p2_status)

        if not state["game_active"]:
            if state["p1_name"] == "Waiting..." or state["p2_name"] == "Waiting...":
                self.canvas.itemconfig(self.status_text, text="Waiting for players to join the queue...")
            else:
                self.canvas.itemconfig(self.status_text, text="Waiting for both players to Ready Up!")
        else:
            self.canvas.itemconfig(self.status_text, text="")

    # ==========================================
    # SERVER BACKEND (Authoritative)
    # ==========================================

    def tcp_server_thread(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', TCP_PORT))
        self.server_socket.listen()
        while self.is_hosting:
            try:
                client_sock, _ = self.server_socket.accept()
                threading.Thread(target=self.handle_client_server_side, args=(client_sock,), daemon=True).start()
            except: break

    def broadcast_server(self, data_dict):
        msg = json.dumps(data_dict) + "\n"
        encoded = msg.encode('utf-8')
        for c in list(self.active_clients.keys()):
            try: c.send(encoded)
            except: self.remove_client(c)

    def handle_client_server_side(self, client_socket):
        buffer = ""
        while self.is_hosting:
            try:
                data = client_socket.recv(1024).decode('utf-8')
                if not data: break
                buffer += data
                
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        packet = json.loads(line)
                        name = self.active_clients.get(client_socket, "Unknown")
                        
                        if packet["type"] == "JOIN":
                            self.active_clients[client_socket] = packet["name"]
                            self.broadcast_server({"type": "CHAT", "msg": f"[SERVER]: {packet['name']} joined as a spectator."})
                            self.update_player_roles()
                            
                        elif packet["type"] == "JOIN_QUEUE":
                            if client_socket not in self.player_queue:
                                self.player_queue.append(client_socket)
                                self.broadcast_server({"type": "CHAT", "msg": f"[SERVER]: {name} joined the play queue."})
                                self.update_player_roles()
                                
                        elif packet["type"] == "READY":
                            if len(self.player_queue) >= 1 and client_socket == self.player_queue[0]:
                                self.game_state["p1_ready"] = True
                            elif len(self.player_queue) >= 2 and client_socket == self.player_queue[1]:
                                self.game_state["p2_ready"] = True
                            self.check_game_start()

                        elif packet["type"] == "CHAT":
                            self.broadcast_server({"type": "CHAT", "msg": f"[{name}]: {packet['msg']}"})
                            
                        elif packet["type"] == "INPUT":
                            is_pressed = packet["pressed"]
                            key = packet["key"]
                            
                            if len(self.player_queue) >= 1 and client_socket == self.player_queue[0]:
                                if key == "Up": self.p1_up = is_pressed
                                elif key == "Down": self.p1_down = is_pressed
                            elif len(self.player_queue) >= 2 and client_socket == self.player_queue[1]:
                                if key == "Up": self.p2_up = is_pressed
                                elif key == "Down": self.p2_down = is_pressed
            except: break
        self.remove_client(client_socket)

    def remove_client(self, client_socket):
        if client_socket in self.active_clients:
            name = self.active_clients[client_socket]
            del self.active_clients[client_socket]
            if client_socket in self.player_queue:
                self.player_queue.remove(client_socket)
            self.broadcast_server({"type": "CHAT", "msg": f"[SERVER]: {name} left."})
            
            self.game_state["p1_ready"] = False
            self.game_state["p2_ready"] = False
            self.game_active = False
            self.update_player_roles()
            client_socket.close()

    def update_player_roles(self):
        self.game_state["p1_name"] = self.active_clients.get(self.player_queue[0], "Waiting...") if len(self.player_queue) > 0 else "Waiting..."
        self.game_state["p2_name"] = self.active_clients.get(self.player_queue[1], "Waiting...") if len(self.player_queue) > 1 else "Waiting..."

    def check_game_start(self):
        if len(self.player_queue) >= 2 and self.game_state["p1_ready"] and self.game_state["p2_ready"]:
            self.game_active = True
            self.reset_ball()
            self.broadcast_server({"type": "CHAT", "msg": f"[GAME]: Match starting! {self.game_state['p1_name']} vs {self.game_state['p2_name']}"})

    def reset_ball(self):
        self.game_state["b_x"] = 380
        self.game_state["b_y"] = 200
        self.game_state["b_dx"] = 6 if self.game_state["b_dx"] < 0 else -6 

    def server_game_loop(self):
        paddle_speed = 10
        paddle_height = 80
        canvas_height = 400
        
        while self.is_hosting:
            if self.p1_up and self.game_state["p1_y"] > 0:
                self.game_state["p1_y"] -= paddle_speed
            if self.p1_down and self.game_state["p1_y"] < canvas_height - paddle_height:
                self.game_state["p1_y"] += paddle_speed
                
            if self.p2_up and self.game_state["p2_y"] > 0:
                self.game_state["p2_y"] -= paddle_speed
            if self.p2_down and self.game_state["p2_y"] < canvas_height - paddle_height:
                self.game_state["p2_y"] += paddle_speed

            if self.game_active:
                self.game_state["b_x"] += self.game_state["b_dx"]
                self.game_state["b_y"] += self.game_state["b_dy"]

                if self.game_state["b_y"] <= 10 or self.game_state["b_y"] >= 390:
                    self.game_state["b_dy"] *= -1

                if self.game_state["b_x"] <= 55 and (self.game_state["p1_y"] <= self.game_state["b_y"] <= self.game_state["p1_y"] + paddle_height):
                    self.game_state["b_dx"] *= -1
                    self.game_state["b_x"] = 56 

                if self.game_state["b_x"] >= 705 and (self.game_state["p2_y"] <= self.game_state["b_y"] <= self.game_state["p2_y"] + paddle_height):
                    self.game_state["b_dx"] *= -1
                    self.game_state["b_x"] = 704

                if self.game_state["b_x"] < 0:
                    self.game_state["s2"] += 1
                    self.handle_game_over(winner_index=1, loser_index=0) 
                elif self.game_state["b_x"] > 760:
                    self.game_state["s1"] += 1
                    self.handle_game_over(winner_index=0, loser_index=1) 

            state_packet = self.game_state.copy()
            state_packet["type"] = "STATE"
            state_packet["q_len"] = max(0, len(self.player_queue) - 2)
            state_packet["game_active"] = self.game_active
            self.broadcast_server(state_packet)
            
            time.sleep(GAME_TICK_RATE)

    def handle_game_over(self, winner_index, loser_index):
        winner_socket = self.player_queue[winner_index]
        loser_socket = self.player_queue[loser_index]
        winner_name = self.active_clients[winner_socket]
        
        self.broadcast_server({"type": "CHAT", "msg": f"[GAME]: {winner_name} wins the match!"})
        
        self.player_queue.remove(loser_socket)
        self.player_queue.append(loser_socket)
        
        self.game_state["s1"] = 0
        self.game_state["s2"] = 0
        self.game_state["p1_ready"] = False
        self.game_state["p2_ready"] = False
        self.game_active = False 
        self.update_player_roles()
        self.reset_ball()

    def udp_discovery_responder(self, room_name):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.bind(('', UDP_PORT))
        while self.is_hosting:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                if data == DISCOVERY_MSG:
                    self.udp_socket.sendto(f"HOST_HERE|{room_name}".encode('utf-8'), addr)
            except: break

    def cleanup_network(self):
        self.is_hosting = False
        self.game_active = False
        self.p1_up = self.p1_down = self.p2_up = self.p2_down = False
        for s in [self.client_socket, self.server_socket, self.udp_socket]:
            if s:
                try: s.close()
                except: pass
        self.client_socket = self.server_socket = self.udp_socket = None
        self.active_clients.clear()
        self.player_queue.clear()

if __name__ == "__main__":
    root = tk.Tk()
    app = LancChatPongApp(root)
    root.mainloop()