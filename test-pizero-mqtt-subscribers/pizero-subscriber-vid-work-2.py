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
VIDEO_DIR = "/home/wasankds/mqtt-subscribers/videos"
os.makedirs(VIDEO_DIR, exist_ok=True)
ZERO_PORT = 8000

# พินควบคุม (ตรวจสอบให้ตรงกับบอร์ด)
PAN_PIN, TILT_PIN = 17, 27
IN1, IN2, IN3, IN4 = 6, 13, 19, 26

# --- GLOBAL ---
picam2 = None
is_recording = False
current_frame = None
current_jpeg = None
video_writer = None
pi = None
curr_pan, curr_tilt = 1500, 1500
servo_dir = None

def init_hardware():
    """ตั้งค่าพินมอเตอร์ให้พร้อมทำงานทันที"""
    global pi
    os.system("sudo pkill pigpiod; sudo pigpiod")
    time.sleep(1)
    pi = pigpio.pi()
    if not pi.connected:
        print("[!] GPIO Error: Cannot connect to pigpiod")
        return False
    
    # ตั้งพินมอเตอร์เป็น OUTPUT และสั่งให้หยุด (0) ทั้งหมด
    for pin in [IN1, IN2, IN3, IN4]:
        pi.set_mode(pin, pigpio.OUTPUT)
        pi.write(pin, 0)
    
    # ตั้งพินเซอร์โว
    pi.set_servo_pulsewidth(PAN_PIN, curr_pan)
    pi.set_servo_pulsewidth(TILT_PIN, curr_tilt)
    print("[*] Hardware Pins Initialized")
    return True

def wheels(l1, l2, r1, r2):
    """ฟังก์ชันขับมอเตอร์ (เพิ่ม Debug เพื่อเช็คสถานะ)"""
    if pi and pi.connected:
        pi.write(IN1, l1)
        pi.write(IN2, l2)
        pi.write(IN3, r1)
        pi.write(IN4, r2)
        # print(f"Motor State: {l1}{l2}{r1}{r2}")

def capture_loop():
    global current_frame, current_jpeg
    while True:
        try:
            frame = picam2.capture_array()
            if frame is not None:
                current_frame = frame
                _, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 40])
                current_jpeg = jpg.tobytes()
            time.sleep(0.05)
        except:
            time.sleep(0.5)

def stream_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', ZERO_PORT))
    server_sock.listen(1)
    while True:
        conn, addr = server_sock.accept()
        try:
            while True:
                if current_jpeg:
                    conn.sendall(struct.pack("<L", len(current_jpeg)) + current_jpeg)
                time.sleep(0.1)
        except:
            conn.close()

def on_message(client, userdata, msg):
    global is_recording, video_writer, servo_dir
    command = msg.payload.decode().strip().lower()
    
    # --- MOVEMENT (ย้ายขึ้นมาให้ความสำคัญอันดับหนึ่ง) ---
    if command == "forward":    wheels(0, 1, 1, 0)
    elif command == "backward": wheels(1, 0, 0, 1)
    elif command == "left":     wheels(1, 0, 1, 0)
    elif command == "right":    wheels(0, 1, 0, 1)
    elif command in ["stop", "wheels_stop"]: wheels(0, 0, 0, 0)

    # --- RECORDING ---
    elif command in ["rec_start", "start record"]:
        if not is_recording:
            filename = f"{VIDEO_DIR}/bot_{time.strftime('%H%M%S')}.avi"
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            video_writer = cv2.VideoWriter(filename, fourcc, 15.0, (640, 480))
            is_recording = True
            print(f"[*] RECORD START: {filename}")

    elif command in ["rec_stop", "stop record"]:
        if is_recording:
            is_recording = False
            if video_writer:
                video_writer.release()
            print("[*] RECORD STOP")

    # --- SERVO ---
    elif "pan_left" in command:   servo_dir = 'pan_r'
    elif "pan_right" in command:  servo_dir = 'pan_l'
    elif "tilt_up" in command:    servo_dir = 'tilt_u'
    elif "tilt_down" in command:  servo_dir = 'tilt_d'
    elif "servo_stop" in command: servo_dir = None

def servo_loop():
    global curr_pan, curr_tilt
    while True:
        if servo_dir == 'pan_l':   curr_pan = max(500, curr_pan - 35)
        elif servo_dir == 'pan_r': curr_pan = min(2500, curr_pan + 35)
        elif servo_dir == 'tilt_u': curr_tilt = min(2500, curr_tilt + 35)
        elif servo_dir == 'tilt_d': curr_tilt = max(1150, curr_tilt - 35)
        if pi and pi.connected:
            pi.set_servo_pulsewidth(PAN_PIN, curr_pan)
            pi.set_servo_pulsewidth(TILT_PIN, curr_tilt)
        time.sleep(0.05)

def record_worker():
    """ดึงภาพไปเขียนไฟล์แบบเงียบๆ ไม่กวน MQTT"""
    global is_recording, video_writer, current_frame
    while True:
        if is_recording and video_writer is not None and current_frame is not None:
            video_writer.write(current_frame)
        time.sleep(0.06)

if __name__ == "__main__":
    if init_hardware():
        # ตั้งค่ากล้อง
        picam2 = Picamera2()
        config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
        config["transform"].vflip = True
        config["transform"].hflip = True
        picam2.configure(config)
        picam2.start()

        # เริ่ม Thread งานรอง
        threading.Thread(target=capture_loop, daemon=True).start()
        threading.Thread(target=stream_server, daemon=True).start()
        threading.Thread(target=record_worker, daemon=True).start()
        threading.Thread(target=servo_loop, daemon=True).start()

        # งานหลักคือรอรับคำสั่ง MQTT
        client = mqtt.Client()
        client.on_message = on_message
        client.connect(MQTT_BROKER, 1883, 60)
        client.subscribe("robot/control")
        print("[*] System Online. Motors and Camera Ready.")
        client.loop_forever()