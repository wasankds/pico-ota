
""" 
สร้าง Ram Drive ด้วย 
rm -rf /home/wasankds/mqtt-subscribers/videos/*
sudo chmod 777 /home/wasankds/mqtt-subscribers/videos


แก้ไขไฟล์ fstab
sudo nano /etc/fstab

เพิ่มบรรทัดนี้ลงไปท้ายสุด
tmpfs  /home/wasankds/mqtt-subscribers/videos  tmpfs  defaults,noatime,nosuid,size=150m  0  0

สั่ง Mount เพื่อเริ่มใช้งาน
sudo mount -a

ตรวจสอบว่าสำเร็จหรือไม่
df -h | grep videos

"""

import threading
import paho.mqtt.client as mqtt
import pigpio
import time
import os
import socket
import struct
import cv2
import queue
import shutil  # สำหรับย้ายไฟล์
from picamera2 import Picamera2

# --- CONFIGURATION ---
MQTT_BROKER = "192.168.1.100"

# (PiZero2W) แยกโฟลเดอร์ RAM และ Storage จริง
VIDEO_RAM = "/home/wasankds/mqtt-subscribers/videos_ram"       # tmpfs (150MB)
VIDEO_STORAGE = "/home/wasankds/mqtt-subscribers/video_storage" # SD Card
os.makedirs(VIDEO_RAM, exist_ok=True)
os.makedirs(VIDEO_STORAGE, exist_ok=True)

MAX_STORAGE_FILES = 1000 # คุมจำนวนไฟล์บน SD Card
MAX_DURATION = 300       # 5 นาที (กัน RAM เต็ม)
ZERO_PORT = 8000
VID_FPS = 10
VID_WIDTH, VID_HEIGHT = 480, 360 
JPG_QUALITY = 35

PAN_PIN, TILT_PIN = 17, 27
IN1, IN2, IN3, IN4 = 6, 13, 19, 26

# --- GLOBAL VARIABLES ---
picam2 = None
is_recording = False
current_frame = None
current_jpeg = None
video_writer = None
current_filename = "" # เก็บชื่อไฟล์ที่กำลังอัดใน RAM
pi = None

curr_pan, curr_tilt = 1500, 1500
target_pan, target_tilt = 1500, 1500 
STEP = 35  
servo_dir = None
recording_start_time = 0
video_queue = queue.Queue(maxsize=30)

# --- FUNCTIONS ---

def init_hardware():
    global pi
    pi = pigpio.pi()
    if not pi.connected: return False
    for pin in [IN1, IN2, IN3, IN4]:
        pi.set_mode(pin, pigpio.OUTPUT)
        pi.write(pin, 0)
    pi.set_mode(PAN_PIN, pigpio.OUTPUT)
    pi.set_mode(TILT_PIN, pigpio.OUTPUT)
    pi.set_servo_pulsewidth(PAN_PIN, 1500)
    pi.set_servo_pulsewidth(TILT_PIN, 1500)
    return True

def wheels(l1, l2, r1, r2):
    if pi and pi.connected:
        pi.write(IN1, l1)
        pi.write(IN2, l2)
        pi.write(IN3, r1)
        pi.write(IN4, r2)

def manage_storage_cleanup():
    """คุมปริมาณไฟล์บน SD Card (ไม่ให้เต็ม)"""
    files = sorted([os.path.join(VIDEO_STORAGE, f) 
                    for f in os.listdir(VIDEO_STORAGE) if f.endswith('.avi')])
    while len(files) >= MAX_STORAGE_FILES:
        try:
            os.remove(files[0])
            files.pop(0)
        except: break

def stop_recording_proc():
    global is_recording, video_writer, current_filename
    if is_recording:
        is_recording = False
        time.sleep(0.5) # รอให้คิวสุดท้ายเขียนลง RAM เสร็จ
        if video_writer:
            video_writer.release()
            video_writer = None
            
            # ย้ายจาก RAM ไป SD Card
            if os.path.exists(current_filename):
                try:
                    dest = os.path.join(VIDEO_STORAGE, os.path.basename(current_filename))
                    shutil.move(current_filename, dest)
                    print(f"[*] MOVED: {os.path.basename(current_filename)} to SD Card")
                except Exception as e:
                    print(f"[!] Move Error: {e}")
        print("[*] RECORDING STOPPED")

# --- THREAD WORKERS ---

def capture_loop():
    global current_frame, current_jpeg
    while True:
        try:
            frame = picam2.capture_array()
            if frame is not None:
                current_frame = frame
                if is_recording:
                    try: video_queue.put_nowait(frame)
                    except: pass
                _, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPG_QUALITY])
                current_jpeg = jpg.tobytes()
            time.sleep(1.0 / VID_FPS)
        except: time.sleep(0.5)

def record_worker():
    global is_recording, video_writer
    while True:
        if is_recording and video_writer is not None:
            try:
                f = video_queue.get(timeout=0.1)
                video_writer.write(f)
                video_queue.task_done()
            except: continue
        else:
            while not video_queue.empty(): video_queue.get()
            time.sleep(0.2)

def stream_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', ZERO_PORT))
    s.listen(1)
    while True:
        conn, addr = s.accept()
        try:
            while True:
                if current_jpeg:
                    conn.sendall(struct.pack("<L", len(current_jpeg)) + current_jpeg)
                time.sleep(0.1)
        except: conn.close()

def auto_monitor_loop():
    global curr_pan, curr_tilt, target_pan, target_tilt, is_recording, recording_start_time
    while True:
        if is_recording and (time.time() - recording_start_time) >= MAX_DURATION:
            stop_recording_proc()

        if servo_dir == 'pan_l':   target_pan = max(500, target_pan - STEP)
        elif servo_dir == 'pan_r': target_pan = min(2500, target_pan + STEP)
        elif servo_dir == 'tilt_u': target_tilt = min(2500, target_tilt + STEP)
        elif servo_dir == 'tilt_d': target_tilt = max(1150, target_tilt - STEP)

        if curr_pan < target_pan: curr_pan = min(target_pan, curr_pan + STEP)
        elif curr_pan > target_pan: curr_pan = max(target_pan, curr_pan - STEP)
        if curr_tilt < target_tilt: curr_tilt = min(target_tilt, curr_tilt + STEP)
        elif curr_tilt > target_tilt: curr_tilt = max(target_tilt, curr_tilt - STEP)
        
        if pi and pi.connected:
            pi.set_servo_pulsewidth(PAN_PIN, curr_pan)
            pi.set_servo_pulsewidth(TILT_PIN, curr_tilt)
        time.sleep(0.05)

# --- MQTT HANDLER ---

def on_message(client, userdata, msg):
    global is_recording, video_writer, servo_dir, recording_start_time, target_pan, target_tilt, current_filename
    command = msg.payload.decode().strip().lower()
    
    if command == "forward":    wheels(0, 1, 1, 0)
    elif command == "backward": wheels(1, 0, 0, 1)
    elif command == "left":    wheels(0, 1, 0, 1)
    elif command == "right":     wheels(1, 0, 1, 0)
    elif command in ["stop", "wheels_stop"]: wheels(0, 0, 0, 0)

    elif command in ["rec_start", "start record"]:
        if not is_recording:
            manage_storage_cleanup()
            current_filename = f"{VIDEO_RAM}/bot_{time.strftime('%H%m%d_%H%M%S')}.avi"
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            video_writer = cv2.VideoWriter(current_filename, fourcc, VID_FPS, (VID_WIDTH, VID_HEIGHT))
            recording_start_time = time.time()
            is_recording = True
            print(f"[*] RECORDING TO RAM: {current_filename}")

    elif command in ["rec_stop", "stop record"]:
        stop_recording_proc()

    if "center" in command or "servo_center" in command:
        servo_dir = None
        target_pan, target_tilt = 1500, 1500
    elif "pan_left" in command:   servo_dir = 'pan_r'
    elif "pan_right" in command:  servo_dir = 'pan_l'
    elif "tilt_up" in command:    servo_dir = 'tilt_u'
    elif "tilt_down" in command:  servo_dir = 'tilt_d'
    elif "servo_stop" in command: servo_dir = None

# --- MAIN ---
if __name__ == "__main__":
    if init_hardware():
        picam2 = Picamera2()
        config = picam2.create_video_configuration(main={"size": (VID_WIDTH, VID_HEIGHT), "format": "RGB888"})
        config["transform"].vflip = True
        config["transform"].hflip = True
        picam2.configure(config)
        picam2.start()

        threading.Thread(target=capture_loop, daemon=True).start()
        threading.Thread(target=stream_server, daemon=True).start()
        threading.Thread(target=record_worker, daemon=True).start()
        threading.Thread(target=auto_monitor_loop, daemon=True).start()

        client = mqtt.Client()
        client.on_message = on_message
        client.connect(MQTT_BROKER, 1883, 60)
        client.subscribe("robot/control")
        print("[*] ROBOT ONLINE - RAM -> SD STORAGE MODE")
        client.loop_forever()