import threading
import paho.mqtt.client as mqtt
import pigpio
import time
import os
import socket
import struct
import cv2
import queue
from picamera2 import Picamera2

# --- CONFIGURATION ---
MQTT_BROKER = "192.168.1.131"
VIDEO_DIR = "/home/wasankds/mqtt-subscribers/videos"
os.makedirs(VIDEO_DIR, exist_ok=True)
ZERO_PORT = 8000

# พินควบคุม (L298N + Servos)
PAN_PIN, TILT_PIN = 17, 27
IN1, IN2, IN3, IN4 = 6, 13, 19, 26

# การจัดการไฟล์และเวลา
MAX_FILES = 1000
MAX_DURATION = 600  # 10 นาที (วินาที)

# --- GLOBAL VARIABLES ---
picam2 = None
is_recording = False
current_frame = None
current_jpeg = None
video_writer = None
pi = None
curr_pan, curr_tilt = 1500, 1500
servo_dir = None
recording_start_time = 0

# สร้าง Queue สำหรับพักเฟรมวิดีโอ (หัวใจที่ทำให้มอเตอร์ไม่ค้าง)
video_queue = queue.Queue(maxsize=30)

# --- FUNCTIONS ---

def init_hardware():
    """เชื่อมต่อกับ pigpiod และตั้งค่าพิน"""
    global pi
    # หมายเหตุ: pigpiod ของคุณเป็น systemd service อยู่แล้ว จึงไม่ต้องสั่งรันใหม่ในนี้
    pi = pigpio.pi()
    if not pi.connected:
        print("[!] GPIO Error: Cannot connect to pigpiod service")
        return False
    
    for pin in [IN1, IN2, IN3, IN4]:
        pi.set_mode(pin, pigpio.OUTPUT)
        pi.write(pin, 0)
    
    pi.set_servo_pulsewidth(PAN_PIN, curr_pan)
    pi.set_servo_pulsewidth(TILT_PIN, curr_tilt)
    print("[*] Hardware Pins Initialized")
    return True

def wheels(l1, l2, r1, r2):
    """ส่งคำสั่งไปที่มอเตอร์"""
    if pi and pi.connected:
        pi.write(IN1, l1)
        pi.write(IN2, l2)
        pi.write(IN3, r1)
        pi.write(IN4, r2)

def manage_video_storage():
    """ลบไฟล์เก่าทิ้งถ้าจำนวนไฟล์เกิน 1000"""
    files = sorted([os.path.join(VIDEO_DIR, f) 
                    for f in os.listdir(VIDEO_DIR) if f.endswith('.avi')])
    while len(files) >= MAX_FILES:
        try:
            os.remove(files[0])
            print(f"[*] Cleanup: Deleted old record {files[0]}")
            files.pop(0)
        except:
            break

def stop_recording_proc():
    """ฟังก์ชันหยุดบันทึกที่เรียกใช้ได้จากทุกที่"""
    global is_recording, video_writer
    if is_recording:
        is_recording = False
        time.sleep(0.2) # ให้เวลา Thread เขียนภาพสุดท้าย
        if video_writer:
            video_writer.release()
            video_writer = None
        print("[*] RECORDING STOPPED AND SAVED")

# --- THREAD WORKERS ---

def capture_loop():
    """ดึงภาพจากกล้องและส่งเข้า Queue บันทึก"""
    global current_frame, current_jpeg
    while True:
        try:
            frame = picam2.capture_array()
            if frame is not None:
                current_frame = frame
                # ถ้ากำลังอัดวิดีโอ ให้ส่งภาพเข้า Queue ทันที (ไม่รอเขียนไฟล์)
                if is_recording:
                    try:
                        video_queue.put_nowait(frame)
                    except queue.Full:
                        pass # ถ้า CPU เต็ม ยอมข้ามเฟรมวิดีโอดีกว่ามอเตอร์ค้าง

                # ทำ JPEG สำหรับ Stream
                _, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 40])
                current_jpeg = jpg.tobytes()
            time.sleep(0.04) # ~25 FPS
        except:
            time.sleep(0.5)

def record_worker():
    """เขียนวิดีโอลง SD Card โดยดึงจาก Queue (แยกภาระ CPU ออกจากงานมอเตอร์)"""
    global is_recording, video_writer
    while True:
        if is_recording and video_writer is not None:
            try:
                frame_to_write = video_queue.get(timeout=0.1)
                video_writer.write(frame_to_write)
                video_queue.task_done()
            except queue.Empty:
                continue
        else:
            # เคลียร์คิวทิ้งเมื่อไม่ได้อัด
            while not video_queue.empty():
                try: video_queue.get_nowait()
                except: break
            time.sleep(0.2)

def stream_server():
    """ส่งภาพ JPEG ไปหา Client (Pi 5)"""
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

def auto_monitor_loop():
    """คุมเวลาอัดวิดีโอ และคุม Servo"""
    global curr_pan, curr_tilt, is_recording, recording_start_time
    while True:
        # 1. เช็คเวลา (ตัด 10 นาที)
        if is_recording:
            if (time.time() - recording_start_time) >= MAX_DURATION:
                print("[!] Auto-Stop: 10 minutes reached.")
                stop_recording_proc()

        # 2. คำนวณตำแหน่ง Servo
        if servo_dir == 'pan_l':   curr_pan = max(500, curr_pan - 35)
        elif servo_dir == 'pan_r': curr_pan = min(2500, curr_pan + 35)
        elif servo_dir == 'tilt_u': curr_tilt = min(2500, curr_tilt + 35)
        elif servo_dir == 'tilt_d': curr_tilt = max(1150, curr_tilt - 35)
        
        if pi and pi.connected:
            pi.set_servo_pulsewidth(PAN_PIN, curr_pan)
            pi.set_servo_pulsewidth(TILT_PIN, curr_tilt)
        time.sleep(0.05)

# --- MQTT HANDLER ---

def on_message(client, userdata, msg):
    global is_recording, video_writer, servo_dir, recording_start_time
    command = msg.payload.decode().strip().lower()
    
    # มอเตอร์ (ลำดับความสำคัญสูงสุด)
    if command == "forward":    wheels(0, 1, 1, 0)
    elif command == "backward": wheels(1, 0, 0, 1)
    elif command == "left":     wheels(1, 0, 1, 0)
    elif command == "right":    wheels(0, 1, 0, 1)
    elif command in ["stop", "wheels_stop"]: wheels(0, 0, 0, 0)

    # วิดีโอ
    elif command in ["rec_start", "start record"]:
        if not is_recording:
            manage_video_storage()
            filename = f"{VIDEO_DIR}/bot_{time.strftime('%Y%m%d_%H%M%S')}.avi"
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            video_writer = cv2.VideoWriter(filename, fourcc, 15.0, (640, 480))
            recording_start_time = time.time()
            is_recording = True
            print(f"[*] START RECORD: {filename}")

    elif command in ["rec_stop", "stop record"]:
        stop_recording_proc()

    # เซอร์โว
    elif "pan_left" in command:   servo_dir = 'pan_r'
    elif "pan_right" in command:  servo_dir = 'pan_l'
    elif "tilt_up" in command:    servo_dir = 'tilt_u'
    elif "tilt_down" in command:  servo_dir = 'tilt_d'
    elif "servo_stop" in command: servo_dir = None

# --- MAIN ---

if __name__ == "__main__":
    if init_hardware():
        # Setup Camera
        picam2 = Picamera2()
        config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
        config["transform"].vflip = True
        config["transform"].hflip = True
        picam2.configure(config)
        picam2.start()

        # Start All Threads
        threading.Thread(target=capture_loop, daemon=True).start()
        threading.Thread(target=stream_server, daemon=True).start()
        threading.Thread(target=record_worker, daemon=True).start()
        threading.Thread(target=auto_monitor_loop, daemon=True).start()

        # Connect MQTT
        client = mqtt.Client()
        client.on_message = on_message
        client.connect(MQTT_BROKER, 1883, 60)
        client.subscribe("robot/control")
        print("[*] ROBOT ONLINE - ASYNC RECORDING MODE")
        client.loop_forever()