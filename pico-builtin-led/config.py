# config.py

# --- WiFi & OTA ---
WIFI_CONFIGS = [
  ('Galaxy A7189EE', '12345678'),
  ('WK_AIS_2.4G', '0813996766')
]
OTA_USER = "wasankds"
OTA_REPO = "pico-ota"
OTA_DIR  = "pico-builtin-led"
OTA_FILES = ["main.py", "wifi_manager.py", "config.py"]

# --- MQTT Settings ---
MQTT_BROKER = '192.168.1.100'
DEVICE_ID   = "pico-001"
CLIENT_ID   = 'pico-001'

# --- การจัดการ Topic ทั้ง 4 ของคุณ ---
TOPIC_S1_ACTION = DEVICE_ID + "/s1/action"
TOPIC_S1_STATUS = DEVICE_ID + "/s1/status"
TOPIC_QUERY     = DEVICE_ID + "/system/query"
TOPIC_AVAIL     = DEVICE_ID + "/system/availability"