import threading
import paho.mqtt.client as mqtt
import pigpio
import time
import os
import socket
import struct
import cv2
from picamera2 import Picamera2

# --- CONFIG ---
MQTT_BROKER = "192.168.1.131"
PAN_PIN, TILT_PIN = 17, 27
IN1, IN2, IN3, IN4 = 6, 13, 19, 26

PAN_CENTER, TILT_CENTER = 1500, 1500
PAN_MIN, PAN_MAX = 500, 2500
TILT_MAX_UP = 2500
TILT_MAX_DOWN = 1150

CAMERA_FRAMERATE = 20
CAMERA_PORT = 8000
CAMERA_JPEG_QUALITY = 50

pi = None
curr_pan, curr_tilt = PAN_CENTER, TILT_CENTER
servo_move_dir = None
picam2 = None

# --- CAMERA SETUP ---
def setup_camera():
    global picam2
    try:
        print("[*] Starting Camera...")
        picam2 = Picamera2()
        config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
        config["transform"].vflip = True
        config["transform"].hflip = True
        picam2.configure(config)
        picam2.start()
        print("[*] Camera Ready")
    except Exception as e:
        print(f"[!] Camera Error: {e}")

# --- STREAMING ---
def stream_worker():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_sock.bind(('0.0.0.0', CAMERA_PORT))
        server_sock.listen(1)
        while True:
            conn, addr = server_sock.accept()
            try:
                while True:
                    frame = picam2.capture_array('main')
                    _, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), CAMERA_JPEG_QUALITY])
                    data = jpg.tobytes()
                    conn.sendall(struct.pack("<L", len(data)) + data)
                    time.sleep(1.0/CAMERA_FRAMERATE)
            except:
                conn.close()
    except Exception as e:
        print(f"Stream Worker Error: {e}")

# --- WHEELS & SERVO ---
def wheels_control(l1, l2, r1, r2):
    """ฟังก์ชันคุมล้อ TT Motor"""
    if pi and pi.connected:
        pi.write(IN1, l1)
        pi.write(IN2, l2)
        pi.write(IN3, r1)
        pi.write(IN4, r2)
        print(f"[*] Wheels: {l1},{l2},{r1},{r2}")

def on_message(client, userdata, msg):
    global servo_move_dir, curr_pan, curr_tilt
    command = msg.payload.decode()

    # --- Wheel Commands ---
    if command == "forward":    wheels_control(0, 1, 1, 0)
    elif command == "backward": wheels_control(1, 0, 0, 1)
    elif command == "left":     wheels_control(1, 0, 1, 0)
    elif command == "right":    wheels_control(0, 1, 0, 1)
    elif command == "stop":     wheels_control(0, 0, 0, 0)

    # --- Emergency / Servo Stop ---
    elif command == "emergency_stop":
        servo_move_dir = None
        wheels_control(0, 0, 0, 0)
    elif command == "servo_stop":
        servo_move_dir = None

    # --- Servo Reset ---
    elif command == "pan_center":
        servo_move_dir = None
        curr_pan = PAN_CENTER
    elif command == "tilt_center":
        servo_move_dir = None
        curr_tilt = TILT_CENTER

    # --- Servo Move Start ---
    elif "_start" in command:
        if "pan_left" in command:   servo_move_dir = 'pan_r'
        elif "pan_right" in command: servo_move_dir = 'pan_l'
        elif "tilt_up" in command:   servo_move_dir = 'tilt_u'
        elif "tilt_down" in command: servo_move_dir = 'tilt_d'

def servo_loop():
    global curr_pan, curr_tilt
    while True:
        if servo_move_dir == 'pan_l':   curr_pan = max(PAN_MIN, curr_pan - 30)
        elif servo_move_dir == 'pan_r': curr_pan = min(PAN_MAX, curr_pan + 30)
        elif servo_move_dir == 'tilt_u': curr_tilt = min(TILT_MAX_UP, curr_tilt + 30)
        elif servo_move_dir == 'tilt_d': curr_tilt = max(TILT_MAX_DOWN, curr_tilt - 30)
        
        if pi and pi.connected:
            pi.set_servo_pulsewidth(PAN_PIN, curr_pan)
            pi.set_servo_pulsewidth(TILT_PIN, curr_tilt)
        time.sleep(0.05)

if __name__ == "__main__":
    # บังคับรัน pigpiod เพื่อให้คุม GPIO ได้
    os.system("sudo pkill pigpiod")
    time.sleep(0.5)
    os.system("sudo pigpiod")
    time.sleep(1)
    
    pi = pigpio.pi()
    if not pi.connected:
        print("[!] FATAL: PIGPIO not connected!")
    else:
        print("[*] PIGPIO Connected. Ready to move.")

    setup_camera()
    threading.Thread(target=stream_worker, daemon=True).start()
    threading.Thread(target=servo_loop, daemon=True).start()

    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe("robot/control")
    
    print("[*] MQTT Subscribed. Waiting for commands...")
    client.loop_forever()