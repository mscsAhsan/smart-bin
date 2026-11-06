# REDACTED COPY — device IP replaced with a placeholder.
# Do NOT commit files containing Wi-Fi credentials to GitHub.
import tkinter as tk
from threading import Thread, Event
import time
import requests
from PIL import Image, ImageTk
import io
# import serial  <--- DISABLED FOR TESTING
from ultralytics import YOLO

# --------------------------------------------------------------------
# --- CONFIGURATION ---
# --------------------------------------------------------------------
# UPDATE THIS IP ADDRESS to match your ESP32
CAMERA_URL = "http://<ESP32_IP>/capture" 
MODEL_PATH = "best.pt"  



class SmartBinTestApp:
    def __init__(self, master):
        self.master = master
        master.title("MODEL TEST MODE (No Arduino)")
        master.geometry("850x700") # Taller window for the button
        
        self.model = None
        self.placeholder_img = Image.new('RGB', (400, 300), color='gray')
        
        self.setup_ui()
        
        # Start initialization
        self.init_thread = Thread(target=self.initialize_model)
        self.init_thread.daemon = True
        self.init_thread.start()

    def setup_ui(self):
        tk.Label(self.master, text="Model Test Mode", font=('Arial', 24, 'bold')).pack(pady=10)
        
        main_frame = tk.Frame(self.master)
        main_frame.pack(fill='both', expand=True)
        
        # Image Display
        self.photo = ImageTk.PhotoImage(self.placeholder_img)
        self.image_label = tk.Label(main_frame, image=self.photo)
        self.image_label.pack(side='top', pady=10)
        
        # Status & Results
        self.status_var = tk.StringVar(value="Loading Model...")
        tk.Label(self.master, textvariable=self.status_var, font=('Arial', 14), fg="blue").pack(pady=5)
        
        self.pred_var = tk.StringVar(value="...")
        tk.Label(self.master, textvariable=self.pred_var, font=('Arial', 26, 'bold'), fg="red").pack(pady=10)

        # --- THE TEST BUTTON ---
        self.btn_capture = tk.Button(self.master, text="📸 CAPTURE & PREDICT", 
                                     font=('Arial', 18, 'bold'), bg="green", fg="white",
                                     command=self.capture_and_predict, state='disabled')
        self.btn_capture.pack(pady=20, ipadx=20, ipady=10)

    def update_image(self, img):
        display_img = img.resize((400, 300)) 
        self.photo = ImageTk.PhotoImage(display_img)
        self.image_label.config(image=self.photo)

    def initialize_model(self):
        try:
            print(f"Loading {MODEL_PATH}...")
            self.model = YOLO(MODEL_PATH)
            print("Model Loaded!")
            self.status_var.set("Ready! Point camera and click Capture.")
            self.btn_capture.config(state='normal') # Enable button
        except Exception as e:
            self.status_var.set(f"Error Loading Model: {e}")
            print(e)

    def capture_and_predict(self):
        self.status_var.set("Capturing...")
        self.master.update()
        
        try:
            # --- LAG FIX START ---
            # 1. Dummy Capture: Clear the old image from the buffer
            try: 
                requests.get(CAMERA_URL, timeout=2)
            except: 
                pass # We don't care if this fails, just trying to flush the pipe
            
            # Small pause to let the camera sensor reset
            time.sleep(0.1) 
            # --- LAG FIX END ---

            # 2. Real Capture: This one will be fresh!
            response = requests.get(CAMERA_URL, timeout=5)
            
            if response.status_code == 200:
                # Process Image
                img_bytes = io.BytesIO(response.content)
                img = Image.open(img_bytes).convert("RGB")
                self.update_image(img)
                
                # Predict
                results = self.model(img, verbose=False)
                
                top_idx = results[0].probs.top1
                confidence = results[0].probs.top1conf.item() * 100
                detected_name = results[0].names[top_idx]

                # Show Result
                result_text = f"{detected_name.upper()} ({confidence:.1f}%)"
                self.pred_var.set(result_text)
                self.status_var.set(f"Detected: {detected_name}")
                print(f"Test Result: {result_text}")
            else:
                self.status_var.set("Error: ESP32 did not send image.")

        except Exception as e:
            self.status_var.set(f"Connection Error: {e}")
            print(f"Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartBinTestApp(root)
    root.mainloop()