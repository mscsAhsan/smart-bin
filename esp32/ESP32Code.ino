// REDACTED COPY — Wi-Fi SSID/password and device IPs replaced with placeholders.
// Do NOT commit the original files with credentials to GitHub.
#include "WiFi.h"
#include "esp_camera.h"
#include "esp_http_server.h"

// --- YOUR WI-FI CREDENTIALS ---
const char* ssid = "<YOUR_WIFI_SSID>";
const char* password = "<YOUR_WIFI_PASSWORD>";

// --- PIN DEFINITIONS ---
#define FLASH_GPIO_NUM    4
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM       5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

httpd_handle_t server = NULL;

static camera_config_t config = {
    .pin_pwdn = PWDN_GPIO_NUM,
    .pin_reset = RESET_GPIO_NUM,
    .pin_xclk = XCLK_GPIO_NUM,
    .pin_sscb_sda = SIOD_GPIO_NUM,
    .pin_sscb_scl = SIOC_GPIO_NUM,
    .pin_d7 = Y9_GPIO_NUM,
    .pin_d6 = Y8_GPIO_NUM,
    .pin_d5 = Y7_GPIO_NUM,
    .pin_d4 = Y6_GPIO_NUM,
    .pin_d3 = Y5_GPIO_NUM,
    .pin_d2 = Y4_GPIO_NUM,
    .pin_d1 = Y3_GPIO_NUM,
    .pin_d0 = Y2_GPIO_NUM,
    .pin_vsync = VSYNC_GPIO_NUM,
    .pin_href = HREF_GPIO_NUM,
    .pin_pclk = PCLK_GPIO_NUM,
    .xclk_freq_hz = 20000000,
    .ledc_timer = LEDC_TIMER_0,
    .ledc_channel = LEDC_CHANNEL_0,
    .pixel_format = PIXFORMAT_JPEG,
    
    // --- HIGH QUALITY SETTINGS (SXGA 1280x1024) ---
    // We use SXGA as requested (one step below max)
    .frame_size = FRAMESIZE_SXGA, 
    .jpeg_quality = 10,             // 10 is very good quality (lower is better)
    .fb_count = 1,                 
    .grab_mode = CAMERA_GRAB_LATEST 
};

// 1. Capture Handler
esp_err_t handle_capture(httpd_req_t *req) {
    // Capture the image
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Camera Capture Failed");
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }

    // Send the image directly (No Stream wrapper needed here)
    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
    httpd_resp_send(req, (const char *)fb->buf, fb->len);
    
    // Clean up
    esp_camera_fb_return(fb);
    return ESP_OK;
}

// 2. Flash Control Handler
esp_err_t handle_flash(httpd_req_t *req) {
    char buf[10];
    if (httpd_req_get_url_query_str(req, buf, 10) == ESP_OK) {
        if (strstr(buf, "v=1")) digitalWrite(FLASH_GPIO_NUM, HIGH);
        else digitalWrite(FLASH_GPIO_NUM, LOW);
    }
    httpd_resp_send(req, "OK", 2);
    return ESP_OK;
}

void start_web_server() {
    httpd_config_t conf = HTTPD_DEFAULT_CONFIG();
    
    // Increase stack size for handling larger requests if needed
    conf.stack_size = 8192; 

    httpd_uri_t capture_uri = { .uri = "/capture", .method = HTTP_GET, .handler = handle_capture };
    httpd_uri_t flash_uri   = { .uri = "/flash",   .method = HTTP_GET, .handler = handle_flash };

    if (httpd_start(&server, &conf) == ESP_OK) {
        httpd_register_uri_handler(server, &capture_uri);
        httpd_register_uri_handler(server, &flash_uri);
    }
}

void setup() {
    Serial.begin(115200);
    Serial.println("\n\n--- ESP32 STARTING ---");

    pinMode(FLASH_GPIO_NUM, OUTPUT);
    digitalWrite(FLASH_GPIO_NUM, LOW);

    // Safety Check for PSRAM (Required for High Res)
    if(psramFound()){
        config.frame_size = FRAMESIZE_SXGA; // 1280x1024
        config.jpeg_quality = 10;
        config.fb_count = 1;
    } else {
        Serial.println("Warning: No PSRAM found. Lowering resolution to SVGA");
        config.frame_size = FRAMESIZE_SVGA; // 800x600 (Fallback)
        config.jpeg_quality = 12;
        config.fb_count = 1;
    }

    // 1. Init Camera
    if (esp_camera_init(&config) != ESP_OK) {
        Serial.println("CRITICAL ERROR: Camera Init Failed");
        return;
    }

    // 2. Connect Wi-Fi
    WiFi.begin(ssid, password);
    Serial.print("Connecting to Wi-Fi");
    
    int retries = 0;
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        retries++;
        if (retries > 30) {
            Serial.println("\nERROR: Wi-Fi Timeout. Restarting...");
            delay(3000);
            ESP.restart();
        }
    }

    Serial.println("\nSUCCESS: WiFi Connected!");
    start_web_server();
    
    Serial.print("SYSTEM READY! IP: http://");
    Serial.print(WiFi.localIP());
    Serial.println("/capture");

    // Blink Status LED
    pinMode(33, OUTPUT);
    for(int i=0; i<5; i++) {
        digitalWrite(33, LOW); delay(100); digitalWrite(33, HIGH); delay(100);
    }
}

void loop() {
    delay(10);
}