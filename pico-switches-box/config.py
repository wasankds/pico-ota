# config.py

# --- WiFi & OTA ---
WIFI_CONFIGS = [
  ('WK_AIS_2.4G', '0813996766') ,
  ('Galaxy A7189EE', '12345678')
]

# senko OTA Settings
OTA_USER = "wasankds"
OTA_REPO = "pico-ota"
OTA_DIR  = "pico-switches-box"
OTA_FILES = ["main.py",  "wifi_manager.py", "tft_control.py"]

# --- MQTT Settings ---
MQTT_BROKER = '192.168.1.100'
DEVICE_ID   = "pico-002"
CLIENT_ID   = 'pico-002'

# --- การจัดการ Topic ทั้ง 4 ของคุณ ---
TOPIC_S1_ACTION = DEVICE_ID + "/s1/action"
TOPIC_S1_STATUS = DEVICE_ID + "/s1/status"
TOPIC_S2_ACTION = DEVICE_ID + "/s2/action"
TOPIC_S2_STATUS = DEVICE_ID + "/s2/status"
TOPIC_QUERY     = DEVICE_ID + "/system/query"
TOPIC_AVAIL     = DEVICE_ID + "/system/availability"
TOPIC_UPDATE    = DEVICE_ID + "/system/update"
TOPIC_SENSOR_DHT  = DEVICE_ID + "/sensor/dht"

