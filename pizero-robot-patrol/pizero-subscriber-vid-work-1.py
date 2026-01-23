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

# พินควบคุมมอเตอร์
PAN_PIN, TILT_PIN = 17, 27
IN1, IN2, IN3, IN4 = 6, 13, 19, 26

# --- GLOBAL ---
picam2 = None
is_recording = False
current_jpeg = None  # ตัวแปรนี้จะเป็น "หัวใจ" ทั้งส่ง Stream และบันทึก
video_writer = None  # ใช้ OpenCV VideoWriter
pi = None
curr_pan, curr_tilt = 1500, 1500
servo_dir = None

def setup_camera():
    global picam2
    try:
        picam2 = Picamera2()
        config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
        config["transform"].vflip = True
        config["transform"].hflip = True
        picam2.configure(config)
        picam2.start()
        print("[*] Camera Online (MJPEG Mode)")
    except Exception as e:
        print(f"[!] Camera Error: {e}")

def stream_server():
    """ส่งภาพ JPEG จากตัวแปรกลางไปให้ผู้ใช้"""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', ZERO_PORT))
    server_sock.listen(1)
    while True:
        conn, addr = server_sock.accept()
        try:
            while True:
                if current_jpeg is not None:
                    conn.sendall(struct.pack("<L", len(current_jpeg)) + current_jpeg)
                time.sleep(0.1) # 10 FPS
        except:
            conn.close()

def capture_loop():
    """ดึงภาพจากกล้อง แปลงเป็น JPEG ครั้งเดียว แล้วแชร์ให้ทั้ง Stream และ Record"""
    global current_jpeg, video_writer, is_recording
    while True:
        try:
            frame = picam2.capture_array()
            if frame is not None:
                # แปลงเป็น JPEG ครั้งเดียว ลดภาระ CPU
                _, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                current_jpeg = jpg.tobytes()
                
                # ถ้ากำลังบันทึก ให้เอาเฟรมนี้เขียนลงไฟล์วิดีโอ
                if is_recording and video_writer is not None:
                    video_writer.write(frame)
                    
            time.sleep(0.05)
        except Exception as e:
            print(f"Capture Error: {e}")
            time.sleep(1)

def on_message(client, userdata, msg):
    global is_recording, video_writer, servo_dir
    command = msg.payload.decode().strip().lower()
    print(f"DEBUG: Command -> {command}")

    # --- RECORDING (บันทึกเป็น AVI/MJPEG ผ่าน OpenCV) ---
    if command in ["rec_start", "start record"]:
        if not is_recording:
            filename = f"{VIDEO_DIR}/bot_{time.strftime('%H%M%S')}.avi"
            # ใช้ MJPG codec ซึ่งเบามากสำหรับ CPU
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            video_writer = cv2.VideoWriter(filename, fourcc, 10.0, (640, 480))
            is_recording = True
            print(f"[*] START RECORDING (MJPEG): {filename}")

    elif command in ["rec_stop", "stop record"]:
        if is_recording:
            is_recording = False
            time.sleep(0.2)
            if video_writer:
                video_writer.release()
                video_writer = None
            print("[*] STOP RECORDING")

    # --- WHEELS CONTROL (ตรวจสอบพินให้แม่นยำ) ---
    elif command == "forward":  wheels(0, 1, 1, 0)
    elif command == "backward": wheels(1, 0, 0, 1)
    elif command == "left":     wheels(1, 0, 1, 0)
    elif command == "right":    wheels(0, 1, 0, 1)
    elif command in ["stop", "wheels_stop"]: wheels(0, 0, 0, 0)

    # --- SERVO CONTROL ---
    elif "pan_left" in command:   servo_dir = 'pan_r'
    elif "pan_right" in command:  servo_dir = 'pan_l'
    elif "tilt_up" in command:    servo_dir = 'tilt_u'
    elif "tilt_down" in command:  servo_dir = 'tilt_d'
    elif "servo_stop" in command: servo_dir = None

def wheels(l1, l2, r1, r2):
    if pi and pi.connected:
        pi.write(IN1, l1); pi.write(IN2, l2); pi.write(IN3, r1); pi.write(IN4, r2)

def servo_loop():
    global curr_pan, curr_tilt
    while True:
        if servo_dir == 'pan_l':   curr_pan = max(500, curr_pan - 40)
        elif servo_dir == 'pan_r': curr_pan = min(2500, curr_pan + 40)
        elif servo_dir == 'tilt_u': curr_tilt = min(2500, curr_tilt + 40)
        elif servo_dir == 'tilt_d': curr_tilt = max(1150, curr_tilt - 40)
        if pi and pi.connected:
            pi.set_servo_pulsewidth(PAN_PIN, curr_pan)
            pi.set_servo_pulsewidth(TILT_PIN, curr_tilt)
        time.sleep(0.05)

if __name__ == "__main__":
    # ล้างสถานะเก่า
    os.system("sudo pkill pigpiod; sudo pigpiod")
    time.sleep(1)
    pi = pigpio.pi()
    
    setup_camera()
    
    # รันงานแยก Thread
    threading.Thread(target=stream_server, daemon=True).start()
    threading.Thread(target=capture_loop, daemon=True).start()
    threading.Thread(target=servo_loop, daemon=True).start()

    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe("robot/control")
    print("[*] System Ready - No-Lag MJPEG Mode")
    client.loop_forever()