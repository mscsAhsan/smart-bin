// REDACTED COPY — Wi-Fi SSID/password and device IPs replaced with placeholders.
// Do NOT commit the original files with credentials to GitHub.
#include <LiquidCrystal_I2C.h>
#include <Servo.h>

// --- CONFIGURATION ---
LiquidCrystal_I2C lcd(0x27, 16, 2); 

Servo servoPaper;   // Pin 4
Servo servoPlastic; // Pin 5
Servo servoFood;    // Pin 6

const int NEUTRAL_POS = 90; 
const int OPEN_POS = 0;     

int trig = 9;       
int echo = 10;      
int conveyorPin = 8; 
int ledPin = 7;     // LED Strips (via Transistor)

void setup() {
  Serial.begin(9600); 

  lcd.init();
  lcd.backlight();
  lcd.print("System Online");
  
  pinMode(trig, OUTPUT);
  pinMode(echo, INPUT);
  pinMode(conveyorPin, OUTPUT);
  pinMode(ledPin, OUTPUT);

  servoPaper.attach(4);   
  servoPlastic.attach(5); 
  servoFood.attach(6);    

  resetServos(); 
  
  // Flash lights on boot to confirm wiring
  digitalWrite(ledPin, HIGH); delay(500); digitalWrite(ledPin, LOW);
}

long getDistance() {
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);
  long duration = pulseIn(echo, HIGH);
  return duration * 0.034 / 2;
}

void resetServos() {
  servoPlastic.write(NEUTRAL_POS);
  servoPaper.write(NEUTRAL_POS);
  servoFood.write(NEUTRAL_POS);
}

void loop() {
  long dist = getDistance();

  // --- 1. AUTOMATIC MODE (Sensor Trigger) ---
  if (dist > 0 && dist < 20) {
    digitalWrite(ledPin, HIGH); // Auto Light ON
    
    lcd.clear();
    lcd.print("Waste Detected");
    lcd.setCursor(0, 1);
    lcd.print("Aligning...");

    delay(3000); 

    Serial.println("D"); // Tell Python to capture
    
    // Note: Light stays ON until Python sends a result or manual 'l' command
    delay(1000); 
  }

  // --- 2. COMMAND MODE (From Python) ---
  if (Serial.available()) {
    char cmd = Serial.read(); 
    
    // Skip empty characters
    if(cmd == '\n' || cmd == '\r' || cmd == ' ') return;

    // --- NEW: LIGHT CONTROL COMMANDS ---
    if (cmd == 'L') {
      digitalWrite(ledPin, HIGH); // Force Light ON
      return;
    }
    if (cmd == 'l') { // Lowercase L
      digitalWrite(ledPin, LOW);  // Force Light OFF
      return;
    }
    // -----------------------------------

    // --- SORTING COMMANDS ---
    // If we receive a sorting command, it means picture is taken. Turn Light OFF.
    digitalWrite(ledPin, LOW); 

    lcd.clear();
    lcd.print("Classified: ");
    digitalWrite(conveyorPin, HIGH); 

    if (cmd == 'A') { 
      lcd.print("Paper");
      servoPaper.write(OPEN_POS);
    } 
    else if (cmd == 'P') { 
      lcd.print("Plastic");
      servoPlastic.write(OPEN_POS);
    } 
    else if (cmd == 'F') { 
      lcd.print("Food");
      servoFood.write(OPEN_POS);
    } 
    else if (cmd == 'O') { 
      lcd.print("Other");
    }

    delay(5000); 
    digitalWrite(conveyorPin, LOW); 
    resetServos();
    
    while(Serial.available()) { Serial.read(); }
    lcd.clear();
    lcd.print("System Ready");
  }
}