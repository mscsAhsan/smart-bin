# REDACTED COPY — device IP replaced with a placeholder.
# Do NOT commit files containing Wi-Fi credentials to GitHub.
import tkinter as tk
from tkinter import ttk, scrolledtext
from threading import Thread, Event
import time
import requests
from PIL import Image, ImageTk, ImageDraw, ImageFont
import io
import serial
import json
import os
from ultralytics import YOLO

# --------------------------------------------------------------------
# --- CONFIGURATION ---
# --------------------------------------------------------------------
ARDUINO_PORT = 'COM5'            # CHECK DEVICE MANAGER
ARDUINO_BAUD = 9600
CAMERA_URL = "http://<ESP32_IP>/capture" # ESP32 IP
MODEL_PATH = "best.pt"           
STATS_FILE = "waste_stats.json"

# --------------------------------------------------------------------
# --- THEME: "CYBER HUD" ---
# --------------------------------------------------------------------
COLOR_BG = "#050505"        # Pure Black
COLOR_PANEL = "#111111"     # Dark Panel
COLOR_ACCENT = "#00FFC8"    # Cyber Cyan
COLOR_WARN = "#FFB800"      # Amber
COLOR_ERR = "#FF3333"       # Red
COLOR_TEXT = "#E0E0E0"
COLOR_DIM = "#444444"

FONT_HUD = ("Consolas", 12, "bold")
FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_DATA = ("Segoe UI", 32, "bold")

COMMAND_MAP = {"plastic": "P", "paper": "A", "food": "F", "others": "O"}

class SmartBinHUDApp:
    def __init__(self, master):
        self.master = master
        self.setup_window()
        self.setup_styles()
        
        self.is_running = Event()
        self.is_running.set()
        self.model = None
        self.arduino = None
        
        # Default "No Signal" Image
        self.current_img = Image.new('RGB', (640, 480), color='#080808')
        
        # Initial Stats (Reset)
        self.stats = {"plastic": 0, "paper": 0, "food": 0, "others": 0}

        # 1. CREATE LAYOUT FIRST
        self.create_layout()
        
        # 2. DRAW INITIAL HUD
        self.draw_hud_overlay(self.current_img, "SYSTEM READY", 0)
        self.update_camera_display(self.current_img)

        # 3. NOW LOAD STATS
        self.load_stats()
        
        # 4. START BACKEND
        self.init_thread = Thread(target=self.initialize_system)
        self.init_thread.daemon = True
        self.init_thread.start()

    def setup_window(self):
        self.master.title("🟢 SMART BIN // AI VISION SYSTEM")
        self.master.geometry("1300x800")
        self.master.configure(bg=COLOR_BG)
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("HUD.Horizontal.TProgressbar", 
                        foreground=COLOR_ACCENT, background=COLOR_ACCENT, 
                        troughcolor=COLOR_PANEL, thickness=6, borderwidth=0)

    def create_layout(self):
        # --- TOP HEADER ---
        header = tk.Frame(self.master, bg=COLOR_BG, height=60)
        header.pack(fill='x', padx=20, pady=10)
        
        tk.Label(header, text="AI VISION CONTROL", font=FONT_TITLE, fg=COLOR_TEXT, bg=COLOR_BG).pack(side='left')
        
        # Status Lights
        self.status_frame = tk.Frame(header, bg=COLOR_BG)
        self.status_frame.pack(side='right')
        self.led_arduino = self.create_led(self.status_frame, "HARDWARE")
        self.led_ai = self.create_led(self.status_frame, "NEURAL NET")

        # --- MAIN CONTAINER ---
        container = tk.Frame(self.master, bg=COLOR_BG)
        container.pack(fill='both', expand=True, padx=20, pady=10)

        # --- LEFT SIDEBAR (STATS) ---
        sidebar = tk.Frame(container, bg=COLOR_PANEL, width=300, padx=15, pady=15)
        sidebar.pack(side='left', fill='y', padx=(0, 15))
        sidebar.pack_propagate(False) # Force width

        self.create_sidebar_content(sidebar)

        # --- RIGHT AREA (CAMERA + LOG) ---
        right_area = tk.Frame(container, bg=COLOR_BG)
        right_area.pack(side='right', fill='both', expand=True)

        # Camera Panel
        cam_panel = tk.Frame(right_area, bg=COLOR_PANEL, padx=5, pady=5)
        cam_panel.pack(fill='both', expand=True)
        
        self.lbl_camera = tk.Label(cam_panel, bg="#000")
        self.lbl_camera.pack(fill='both', expand=True)

        # Bottom Terminal Log
        log_panel = tk.Frame(right_area, bg=COLOR_BG, height=150)
        log_panel.pack(fill='x', pady=(15, 0))
        
        tk.Label(log_panel, text="> SYSTEM_LOGS", fg=COLOR_DIM, bg=COLOR_BG, font=("Consolas", 10)).pack(anchor='w')
        self.log_text = scrolledtext.ScrolledText(log_panel, height=6, bg="#0a0a0a", fg="#00ff00", 
                                                  font=("Consolas", 9), relief="flat", state='disabled')
        self.log_text.pack(fill='both')

    def create_led(self, parent, label):
        frame = tk.Frame(parent, bg=COLOR_BG)
        frame.pack(side='left', padx=10)
        lbl = tk.Label(frame, text="●", fg=COLOR_DIM, bg=COLOR_BG, font=("Arial", 16))
        lbl.pack(side='left')
        tk.Label(frame, text=label, fg=COLOR_DIM, bg=COLOR_BG, font=("Segoe UI", 8, "bold")).pack(side='left', padx=5)
        return lbl

    def create_sidebar_content(self, parent):
        # Result Box
        tk.Label(parent, text="DETECTED OBJECT", fg=COLOR_ACCENT, bg=COLOR_PANEL, font=("Segoe UI", 9)).pack(anchor='w')
        self.lbl_result = tk.Label(parent, text="--", fg="white", bg=COLOR_PANEL, font=FONT_DATA)
        self.lbl_result.pack(anchor='w', pady=(0, 20))

        # Confidence
        tk.Label(parent, text="CONFIDENCE LEVEL", fg=COLOR_ACCENT, bg=COLOR_PANEL, font=("Segoe UI", 9)).pack(anchor='w')
        self.lbl_conf = tk.Label(parent, text="0%", fg="white", bg=COLOR_PANEL, font=("Segoe UI", 18))
        self.lbl_conf.pack(anchor='w')
        self.progress = ttk.Progressbar(parent, orient='horizontal', mode='determinate', style="HUD.Horizontal.TProgressbar")
        self.progress.pack(fill='x', pady=(5, 30))

        # Stats Grid - FIXED THE ERROR HERE (mb=10 -> pady=(0, 10))
        tk.Label(parent, text="SESSION DATA", fg=COLOR_ACCENT, bg=COLOR_PANEL, font=("Segoe UI", 9)).pack(anchor='w', pady=(0, 10))
        
        self.lbl_plastic = self.add_stat_row(parent, "PLASTIC", "#4fc3f7")
        self.lbl_paper = self.add_stat_row(parent, "PAPER", "#aed581")
        self.lbl_food = self.add_stat_row(parent, "FOOD", "#ffb74d")
        self.lbl_other = self.add_stat_row(parent, "OTHER", "#e57373")

        # Buttons
        tk.Button(parent, text="RESET DATA", bg="#222", fg="white", relief="flat", command=self.reset_stats).pack(fill='x', pady=(30, 5))
        self.btn_capture = tk.Button(parent, text="MANUAL SCAN [SPACE]", bg=COLOR_ACCENT, fg="black", font=("Segoe UI", 10, "bold"), 
                                     relief="flat", command=self.capture_and_predict, state='disabled')
        self.btn_capture.pack(fill='x')
        
        # Bind spacebar
        self.master.bind('<space>', lambda e: self.capture_and_predict())

    def add_stat_row(self, parent, label, color):
        frame = tk.Frame(parent, bg=COLOR_PANEL)
        frame.pack(fill='x', pady=2)
        tk.Label(frame, text=label, fg="#888", bg=COLOR_PANEL, width=10, anchor='w').pack(side='left')
        lbl = tk.Label(frame, text="0", fg=color, bg=COLOR_PANEL, font=("Consolas", 12, "bold"))
        lbl.pack(side='right')
        return lbl

    # --- HUD DRAWING LOGIC ---
    def draw_hud_overlay(self, img, text, conf):
        draw = ImageDraw.Draw(img)
        w, h = img.size
        
        # Draw "Brackets" (Corners)
        color = COLOR_ACCENT
        thick = 3
        len_line = 40
        m = 20 # Margin
        
        # Top Left
        draw.line([(m, m), (m + len_line, m)], fill=color, width=thick)
        draw.line([(m, m), (m, m + len_line)], fill=color, width=thick)
        # Top Right
        draw.line([(w-m, m), (w-m - len_line, m)], fill=color, width=thick)
        draw.line([(w-m, m), (w-m, m + len_line)], fill=color, width=thick)
        # Bottom Left
        draw.line([(m, h-m), (m + len_line, h-m)], fill=color, width=thick)
        draw.line([(m, h-m), (m, h-m - len_line)], fill=color, width=thick)
        # Bottom Right
        draw.line([(w-m, h-m), (w-m - len_line, h-m)], fill=color, width=thick)
        draw.line([(w-m, h-m), (w-m, h-m - len_line)], fill=color, width=thick)

        # Draw Crosshair
        cx, cy = w//2, h//2
        draw.line([(cx-10, cy), (cx+10, cy)], fill=color, width=1)
        draw.line([(cx, cy-10), (cx, cy+10)], fill=color, width=1)
        
        # Draw Text Overlay
        if text:
            draw.text((m+5, m+5), f"TARGET: {text}", fill=color)
            draw.text((m+5, m+20), f"CONF: {conf:.1f}%", fill=color)

    def update_camera_display(self, img):
        self.photo = ImageTk.PhotoImage(img)
        self.lbl_camera.config(image=self.photo)

    # --- BACKEND ---
    def log(self, msg):
        timestamp = time.strftime('%H:%M:%S')
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"[{timestamp}] > {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def load_stats(self):
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, 'r') as f: self.stats = json.load(f)
            except: pass
        self.update_stats_ui()

    def save_stats(self):
        with open(STATS_FILE, 'w') as f: json.dump(self.stats, f)

    def reset_stats(self):
        self.stats = {k: 0 for k in self.stats}
        self.save_stats()
        self.update_stats_ui()

    def update_stats_ui(self):
        self.lbl_plastic.config(text=str(self.stats['plastic']))
        self.lbl_paper.config(text=str(self.stats['paper']))
        self.lbl_food.config(text=str(self.stats['food']))
        self.lbl_other.config(text=str(self.stats['others']))

    def initialize_system(self):
        self.log("BOOT SEQUENCE INITIATED...")
        
        # Load AI
        try:
            self.model = YOLO(MODEL_PATH)
            self.log("NEURAL NETWORK [ONLINE]")
            self.led_ai.config(fg=COLOR_ACCENT) # Green light
        except Exception as e:
            self.log(f"AI FAILURE: {e}")
            self.led_ai.config(fg=COLOR_ERR)
            return

        # Connect Arduino
        try:
            self.arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
            time.sleep(2)
            self.log(f"SERIAL LINK ESTABLISHED ({ARDUINO_PORT})")
            self.led_arduino.config(fg=COLOR_ACCENT)
            self.btn_capture.config(state='normal')
            
            self.monitor_thread = Thread(target=self.serial_monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
        except:
            self.log("HARDWARE LINK FAILED - DEMO MODE")
            self.led_arduino.config(fg=COLOR_WARN) # Yellow light
            self.btn_capture.config(state='normal')

    def capture_and_predict(self):
        self.log("SCANNING TARGET...")
        try:
            try: requests.get(CAMERA_URL, timeout=1.5)
            except: pass
            
            time.sleep(0.15)
            response = requests.get(CAMERA_URL, timeout=5)
            
            if response.status_code == 200:
                img_bytes = io.BytesIO(response.content)
                img = Image.open(img_bytes).convert("RGB")
                
                # AI Predict
                results = self.model(img, verbose=False)
                top_idx = results[0].probs.top1
                confidence = results[0].probs.top1conf.item() * 100
                name = results[0].names[top_idx].upper()

                # Logic
                cmd = COMMAND_MAP.get(name.lower(), 'O')
                if confidence < 60:
                    name = "UNIDENTIFIED"
                    cmd = 'O'
                
                # Update Stats
                key = name.lower() if name.lower() in self.stats else 'others'
                self.stats[key] += 1
                self.save_stats()
                self.update_stats_ui()

                # Draw HUD
                display_img = img.resize((800, 600))
                self.draw_hud_overlay(display_img, name, confidence)
                self.update_camera_display(display_img)

                # Update Sidebar
                self.lbl_result.config(text=name)
                self.lbl_conf.config(text=f"{confidence:.1f}%")
                self.progress['value'] = confidence
                
                self.log(f"TARGET: {name} // ACTION: {cmd}")

                if self.arduino and self.arduino.is_open:
                    self.arduino.write(cmd.encode())

        except Exception as e:
            self.log(f"ERROR: {e}")

    def serial_monitor_loop(self):
        while self.is_running.is_set():
            if self.arduino and self.arduino.in_waiting:
                try:
                    line = self.arduino.readline().decode().strip()
                    if line == "D":
                        self.log("SENSOR TRIGGER DETECTED")
                        self.master.after(0, self.capture_and_predict)
                except: pass
            time.sleep(0.05)

    def on_closing(self):
        self.is_running.clear()
        if self.arduino: self.arduino.close()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartBinHUDApp(root)
    root.mainloop()