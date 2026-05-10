import tkinter as tk
from tkinter import ttk, messagebox
import socket
import select
import json
import os

class ScrollableFrame(ttk.Frame):
    """Helper class to make tabs scrollable for mobile phone screens."""
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self, bg="#e2e8f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#e2e8f0")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=canvas.winfo_reqwidth())
        
        # Bind resize to keep cards full width
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas.find_withtag('all')[0], width=e.width))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

class ModbusPollClone:
    def __init__(self, root):
        self.root = root
        self.root.title("Titan Modbus Master")
        self.root.geometry("400x700") 
        self.root.configure(bg="#ffffff")

        # Config File Path
        self.config_file = "titan_config.json"

        # Network Variables
        self.ip_var = tk.StringVar(value="192.168.1.100")
        self.port_var = tk.IntVar(value=8000)
        self.slave_var = tk.IntVar(value=1)
        
        # State Variables
        self.is_connected = False
        self.sock = None
        self.register_rows = []    
        self.active_configs = []   
        self.card_labels = {}      

        # Build UI
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=[10, 8])
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill="both", padx=5, pady=5)

        # Tabs
        self.tab_dash = tk.Frame(self.notebook, bg="#e2e8f0")
        self.notebook.add(self.tab_dash, text="Dashboard")
        
        self.tab_set = tk.Frame(self.notebook, bg="#f8f9fa")
        self.notebook.add(self.tab_set, text="Settings")

        self.build_settings()
        self.build_dashboard()
        
        # Auto-Load Saved Configuration
        self.load_config()

    # ---------------------------------------------------------
    # CONFIGURATION SAVING & LOADING
    # ---------------------------------------------------------
    def load_config(self):
        """Loads settings from the JSON file if it exists."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    
                    self.ip_var.set(data.get("ip", "192.168.1.100"))
                    self.port_var.set(data.get("port", 8000))
                    self.slave_var.set(data.get("slave", 1))
                    
                    saved_regs = data.get("registers", [])
                    if saved_regs:
                        for reg in saved_regs:
                            self.add_register_row(reg.get("name", ""), reg.get("addr", ""))
                        return # Exit the function so we don't load defaults
            except Exception as e:
                print(f"Error loading config: {e}")

        # If no file exists, load these defaults
        self.add_register_row("PECM Machine", 100)
        self.add_register_row("Case Assembly", 101)

    def save_config(self):
        """Saves current settings to a JSON file."""
        data = {
            "ip": self.ip_var.get(),
            "port": self.port_var.get(),
            "slave": self.slave_var.get(),
            "registers": []
        }
        
        for row in self.register_rows:
            name = row["name"].get().strip()
            addr = row["addr"].get().strip()
            if name and addr:
                data["registers"].append({"name": name, "addr": addr})

        try:
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    # ---------------------------------------------------------
    # SETTINGS UI
    # ---------------------------------------------------------
    def build_settings(self):
        self.set_scroll = ScrollableFrame(self.tab_set)
        self.set_scroll.pack(expand=True, fill="both", padx=5, pady=5)
        self.set_scroll.scrollable_frame.configure(bg="#f8f9fa")

        # Top Network Config
        net_frame = tk.Frame(self.set_scroll.scrollable_frame, bg="#f8f9fa", pady=10)
        net_frame.pack(fill="x", padx=10)

        tk.Label(net_frame, text="Gateway IP:", bg="#f8f9fa", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Entry(net_frame, textvariable=self.ip_var, font=("Segoe UI", 12)).pack(fill="x", pady=(0, 10))

        tk.Label(net_frame, text="Port (e.g., 8000 or 502):", bg="#f8f9fa", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Entry(net_frame, textvariable=self.port_var, font=("Segoe UI", 12)).pack(fill="x", pady=(0, 10))

        tk.Label(net_frame, text="Slave ID:", bg="#f8f9fa", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Entry(net_frame, textvariable=self.slave_var, font=("Segoe UI", 12)).pack(fill="x", pady=(0, 15))

        self.btn_connect = tk.Button(net_frame, text="CONNECT & SAVE", bg="#16a34a", fg="white", font=("Segoe UI", 12, "bold"), pady=10, command=self.toggle_connection)
        self.btn_connect.pack(fill="x")

        tk.Frame(self.set_scroll.scrollable_frame, height=2, bg="#dee2e6").pack(fill="x", pady=15)

        # Register Config Header
        reg_head = tk.Frame(self.set_scroll.scrollable_frame, bg="#f8f9fa")
        reg_head.pack(fill="x", padx=10)
        tk.Label(reg_head, text="Registers to Read", bg="#f8f9fa", font=("Segoe UI", 14, "bold"), fg="#334155").pack(side="left")
        tk.Button(reg_head, text="+ ADD", bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"), command=self.add_register_row).pack(side="right")

        self.reg_container = tk.Frame(self.set_scroll.scrollable_frame, bg="#f8f9fa")
        self.reg_container.pack(fill="x", padx=10, pady=10)

    def add_register_row(self, default_name="", default_addr=""):
        row_frame = tk.Frame(self.reg_container, bg="#ffffff", bd=1, relief="solid", pady=10, padx=10)
        row_frame.pack(fill="x", pady=5)

        tk.Label(row_frame, text="Name:", bg="#ffffff", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        name_entry = tk.Entry(row_frame, font=("Segoe UI", 10))
        name_entry.insert(0, default_name)
        name_entry.pack(fill="x", pady=(0, 5))

        tk.Label(row_frame, text="Address:", bg="#ffffff", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        addr_frame = tk.Frame(row_frame, bg="#ffffff")
        addr_frame.pack(fill="x")
        
        addr_entry = tk.Entry(addr_frame, font=("Segoe UI", 10))
        addr_entry.insert(0, default_addr)
        addr_entry.pack(side="left", fill="x", expand=True)

        btn_rm = tk.Button(addr_frame, text="DEL", bg="#ef4444", fg="white", font=("Segoe UI", 9, "bold"), command=lambda f=row_frame: self.remove_register_row(f))
        btn_rm.pack(side="right", padx=(10, 0))

        self.register_rows.append({"frame": row_frame, "name": name_entry, "addr": addr_entry})

    def remove_register_row(self, frame_to_remove):
        frame_to_remove.destroy()
        self.register_rows = [row for row in self.register_rows if row["frame"] != frame_to_remove]

    # ---------------------------------------------------------
    # DASHBOARD UI
    # ---------------------------------------------------------
    def build_dashboard(self):
        self.status_lbl = tk.Label(self.tab_dash, text="SYSTEM OFFLINE", fg="#dc3545", bg="#e2e8f0", font=("Segoe UI", 14, "bold"))
        self.status_lbl.pack(pady=10)
        
        self.dash_scroll = ScrollableFrame(self.tab_dash)
        self.dash_scroll.pack(expand=True, fill="both", padx=5, pady=5)
        
        tk.Label(self.tab_dash, text="LIVE HEX DEBUGGER:", bg="#e2e8f0", fg="#64748b", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10)
        self.debug_text = tk.Text(self.tab_dash, height=4, bg="#0a0a0a", fg="#4ade80", font=("Consolas", 8))
        self.debug_text.pack(fill="x", padx=10, pady=(0, 10))
        self.debug_text.insert(tk.END, "Awaiting connection...\n")

    def generate_dashboard_cards(self):
        for widget in self.dash_scroll.scrollable_frame.winfo_children():
            widget.destroy()
        self.card_labels.clear()

        for config in self.active_configs:
            card = tk.Frame(self.dash_scroll.scrollable_frame, relief="flat", bg="white", padx=15, pady=15)
            card.pack(fill="x", padx=10, pady=8)
            
            tk.Frame(card, bg="#0284c7", height=4).pack(fill="x", side="top", pady=(0, 10))

            tk.Label(card, text=config['name'], bg="white", fg="#0f172a", font=("Segoe UI", 14, "bold")).pack()
            tk.Label(card, text=f"Register D{config['addr']}", bg="white", fg="#64748b", font=("Segoe UI", 10)).pack(pady=(0, 10))
            
            lbl_val = tk.Label(card, text="--", bg="white", fg="#cbd5e1", font=("Consolas", 36, "bold"))
            lbl_val.pack()
            
            self.card_labels[config['addr']] = lbl_val

    def log_debug(self, msg):
        self.debug_text.insert(tk.END, msg + "\n")
        lines = self.debug_text.get("1.0", tk.END).split("\n")
        if len(lines) > 5:
            self.debug_text.delete("1.0", "2.0")
        self.debug_text.see(tk.END)

    # ---------------------------------------------------------
    # CONNECTION LOGIC
    # ---------------------------------------------------------
    def connect_socket(self):
        if self.sock:
            try: self.sock.close()
            except: pass
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(3.0) 
        self.sock.connect((self.ip_var.get(), self.port_var.get()))

    def toggle_connection(self):
        if not self.is_connected:
            self.active_configs = []
            for row in self.register_rows:
                name = row["name"].get().strip()
                addr_str = row["addr"].get().strip()
                if name and addr_str.isdigit():
                    self.active_configs.append({"name": name, "addr": int(addr_str)})
            
            if not self.active_configs:
                messagebox.showerror("Error", "Please add at least one valid register.")
                return

            # Save the valid configuration to our file!
            self.save_config()

            try:
                self.connect_socket()
                self.is_connected = True
                self.status_lbl.config(text="CONNECTED & POLLING", fg="#16a34a")
                self.btn_connect.config(text="DISCONNECT", bg="#dc3545")
                self.notebook.select(self.tab_dash) 
                
                self.generate_dashboard_cards() 
                self.log_debug("--- CONNECTED ---")
                self.poll_data() 
            except Exception as e:
                self.status_lbl.config(text="CONNECTION FAILED", fg="#dc3545")
                self.notebook.select(self.tab_dash)
                self.log_debug(f"Err: {e}")
        else:
            self.is_connected = False
            if self.sock: self.sock.close()
            self.status_lbl.config(text="SYSTEM OFFLINE", fg="#dc3545")
            self.btn_connect.config(text="CONNECT & SAVE", bg="#16a34a")
            self.log_debug("--- DISCONNECTED ---")
            for lbl in self.card_labels.values():
                lbl.config(text="--", fg="#cbd5e1")

    def poll_data(self):
        if not self.is_connected:
            return
        
        slave_id = self.slave_var.get()
        needs_reconnect = False

        for config in self.active_configs:
            if needs_reconnect: break 
            reg = config['addr']
            lbl = self.card_labels[reg]

            try:
                while True:
                    r, _, _ = select.select([self.sock], [], [], 0.0)
                    if r: self.sock.recv(1024)
                    else: break

                req = bytearray([
                    0x00, 0x01, 
                    0x00, 0x00, 
                    0x00, 0x06, 
                    slave_id, 0x03, 
                    (reg >> 8) & 0xFF, reg & 0xFF, 
                    0x00, 0x01
                ])
                self.sock.send(req)
                
                resp = self.sock.recv(1024)
                if not resp: raise Exception("Dropped by gateway")

                hex_str = ' '.join(f'{b:02X}' for b in resp)
                self.log_debug(f"RX(D{reg}): {hex_str[:20]}...")

                if len(resp) >= 11 and resp[7] == 0x03:
                    val = (resp[9] << 8) | resp[10]
                    if val > 32767: val -= 65536 
                    lbl.config(text=str(val), fg="#0f172a") 
                elif len(resp) >= 9 and resp[7] == 0x83:
                    lbl.config(text="ERR", fg="#f59e0b")
                else:
                    lbl.config(text="BAD FMT", fg="#dc3545")
                    
            except socket.timeout:
                lbl.config(text="TIMEOUT", fg="#dc3545")
                self.log_debug(f"Timeout D{reg}")
                needs_reconnect = True
            except Exception as e:
                lbl.config(text="DISCONN", fg="#dc3545")
                needs_reconnect = True
        
        if needs_reconnect and self.is_connected:
            try: self.connect_socket()
            except: pass
                
        self.root.after(1000, self.poll_data)

if __name__ == "__main__":
    root = tk.Tk()
    app = ModbusPollClone(root)
    root.mainloop()
