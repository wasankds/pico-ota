
""" 

MOTION_THRESHOLD
1. ช่วงค่าที่แนะนำ
500 - 2,000 (ไวมาก): ตรวจจับได้แม้กระทั่งแมลงบินผ่าน หรือใบไม้ไหวเบาๆ (อาจจะทำให้เครื่องอัดวิดีโอพร่ำเพรื่อเกินไป)
5,000 - 15,000 (มาตรฐาน): เหมาะสำหรับตรวจจับคนที่เดินผ่านหน้ากล้องในระยะ 2-5 เมตร เป็นค่าเริ่มต้นที่ดีสำหรับใช้งานทั่วไป
30,000 ขึ้นไป (ความไวต่ำ): จะตรวจจับเฉพาะวัตถุขนาดใหญ่ที่อยู่ใกล้กล้องมากๆ เช่น คนเดินประชิดประตู หรือรถยนต์คันใหญ่ๆ

"""

import socket
import cv2
import struct
import time
import os
import threading
import numpy as np

# Import สำหรับ picamera2 เวอร์ชัน 0.3.x
from picamera2 import Picamera2
from picamera2.outputs import FileOutput
from picamera2.encoders import H264Encoder

# --- CONFIGURATION ---
ZERO_PORT = 8000
VIDEO_DIR = "/home/wasankds/eagle-eye-legion-pizero/videos"
MAX_FILES = 100
MOTION_THRESHOLD = 10000    # ปรับเพิ่มถ้ามันบันทึกบ่อยเกินไป
MOTION_IMAGE_WIDTH = 64     # ขนาดภาพจิ๋วสำหรับวิเคราะห์ Motion
MOTION_IMAGE_HEIGHT = 48    # ขนาดภาพจิ๋วสำหรับวิเคราะห์ Motion
RECORD_DURATION = 15        # บันทึกครั้งละ 15 วินาที
STREAM_FPS_NORMAL = 4       # FPS ปกติ (สำหรับการสตรีมไป Pi 5)
STREAM_FPS_RECORDING = 2    # FPS ตอนกำลังอัดวิดีโอ (สำหรับการสตรีมไป Pi 5)
STREAM_JPG_QUALITY = 40     # คุณภาพ JPEG สำหรับสตรีม (0-100)
# ชื่อ user ปกติ (ไม่ใช่ root) เพื่อเปลี่ยนเจ้าของไฟล์หลังอัดเสร็จ
USER = "wasankds"

# สร้างโฟลเดอร์ถ้ายังไม่มี
if not os.path.exists(VIDEO_DIR):
    os.makedirs(VIDEO_DIR)

# --- GLOBAL VARIABLES ---
picam2 = None
is_recording = False
recording_start_time = 0
current_jpeg = None  # เก็บภาพล่าสุดสำหรับส่งสตรีม


def manage_files():
    """ลบไฟล์เก่าถ้าเกินจำนวนที่กำหนด (รันแบบ Background)"""
    files = sorted([os.path.join(VIDEO_DIR, f)
                    for f in os.listdir(VIDEO_DIR) if f.endswith('.h264')])
    while len(files) >= MAX_FILES:
        try:
            os.remove(files[0])
            files.pop(0)
            print(f"[*] Deleted old record: {files[0]}")
        except:
            break


def restart_camera():
    """ฟังก์ชันหัวใจสำคัญ: รีเซ็ต Hardware กล้องเพื่อป้องกันอาการภาพค้าง (ISP Hang)"""
    global picam2
    print("\n[*] Resetting Camera Hardware to prevent hang...")
    try:
        if picam2:
            picam2.stop()
            picam2.close()

        picam2 = Picamera2()
        config = picam2.create_video_configuration(
            # main ใช้สำหรับดึงภาพมาวิเคราะห์ Motion และส่งสตรีม
            main={"size": (640, 480), "format": "RGB888"},
            # lores (เส้นที่ 2) จองไว้สำหรับอัดวิดีโอ H.264 โดยเฉพาะ
            lores={"size": (640, 480), "format": "YUV420"},
        )
        picam2.configure(config)
        picam2.start()
        print("[*] Camera Hardware Restored & Ready.")
    except Exception as e:
        print(f"[!] Critical Error during Camera Restart: {e}")


def stream_server():
    """Server ส่งภาพ JPEG ไปยัง Pi 5 (รันตลอดเวลาใน Thread แยก)"""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', ZERO_PORT))
    server_sock.listen(1)

    print(f"[*] Stream Server active on port {ZERO_PORT}")

    while True:
        conn, addr = server_sock.accept()
        print(f"[*] Pi 5 Connected from {addr}")
        try:
            while True:
                if current_jpeg is not None:
                    msg = current_jpeg
                    conn.sendall(struct.pack("<L", len(msg)) + msg)

                # --- ปรับตรงนี้: เลือกใช้ FPS ตามสถานะการอัด ---
                current_fps = STREAM_FPS_RECORDING if is_recording else STREAM_FPS_NORMAL
                time.sleep(1.0 / current_fps)
        except:
            print("[!] Client disconnected.")
        finally:
            conn.close()


def main():
    global picam2, is_recording, recording_start_time, current_jpeg

    # เริ่มต้นกล้องครั้งแรก
    restart_camera()

    # เริ่ม Thread ส่งภาพไป Pi 5
    threading.Thread(target=stream_server, daemon=True).start()

    avg_frame = None
    last_stream_time = 0
    print("[*] Eagle Eye System Started. Monitoring for motion...")

    while True:
        try:
            # 1. ดึงภาพปัจจุบันจากกล้อง
            frame = picam2.capture_array()

            # 2. แปลงเป็น JPEG เพื่อรอส่งสตรีม (ทำครั้งเดียวเพื่อประหยัด CPU)
            # - ทำ JPEG Encoding ตาม FPS ที่เหมาะสม
            current_time = time.time()
            target_fps = STREAM_FPS_RECORDING if is_recording else STREAM_FPS_NORMAL
            if current_time - last_stream_time > (1.0 / target_fps):
                _, jpg_data = cv2.imencode(
                    '.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), STREAM_JPG_QUALITY])
                current_jpeg = jpg_data.tobytes()
                last_stream_time = current_time

            # --- PART A: MOTION DETECTION ---
            # ย่อภาพจิ๋วเพื่อประหยัด RAM ในการวิเคราะห์ 40,30
            small = cv2.resize(
                frame, (MOTION_IMAGE_WIDTH, MOTION_IMAGE_HEIGHT))
            gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if avg_frame is None:
                avg_frame = gray.copy().astype("float")
                continue

            cv2.accumulateWeighted(gray, avg_frame, 0.5)
            frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(avg_frame))
            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
            motion_score = np.sum(thresh)

            # Debug Score (เปิดทิ้งไว้ดูได้ครับ) - ใช้จริง ปิดไป
            # if int(time.time()) % 2 == 0:print(f"Motion Score: {motion_score}")

            # --- PART B: RECORDING LOGIC ---
            current_time = time.time()

            # ตรวจพบการเคลื่อนไหว -> เริ่มบันทึก
            if motion_score > MOTION_THRESHOLD and not is_recording:
                print(
                    f"[!] MOTION DETECTED ({motion_score})! Starting Recording...")
                is_recording = True
                recording_start_time = current_time

                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f"{VIDEO_DIR}/motion_{timestamp}.h264"

                # คำสั่งอัดวิดีโอสำหรับ picamera2 v0.3.31
                # ใช้ Encoder H264 + ไฟล์ปลายทาง + ระบุดึงข้อมูลจาก stream 'lores'
                encoder = H264Encoder(bitrate=1500000)
                picam2.start_recording(
                    encoder, FileOutput(filename), name="lores")

            # ครบเวลาบันทึก -> หยุดและรีเซ็ตกล้อง
            elif is_recording and (current_time - recording_start_time > RECORD_DURATION):
                print("[*] Stopping Recording and Refreshing Camera...")
                try:
                    picam2.stop_recording()

                    # เปลี่ยนเจ้าของไฟล์เพื่อให้ user ปกติจัดการไฟล์ได้ - เพราะรัน python ด้วย sudo
                    # เปลี่ยน 'wasankds' เป็นชื่อ user ของคุณถ้ามีการเปลี่ยนแปลง
                    os.system(f"chown {USER}:{USER} {filename}")
                    print(f"[*] Ownership changed to {USER}")
                except:
                    pass
                is_recording = False

                # เคลียร์ RAM Cache (ทำงานได้เพราะรันด้วย sudo)
                try:
                    os.system("sync")
                    with open('/proc/sys/vm/drop_caches', 'w') as f:
                        f.write('3')
                    print("[*] RAM Cache Cleared Successfully")
                except Exception as e:
                    print(f"[!] RAM Clear failed: {e}")

                # รีเซ็ต Hardware ทันทีหลังอัดเสร็จ เพื่อไม่ให้ภาพค้าง
                restart_camera()

                # รีเซ็ตตัวแปรพื้นหลัง เพื่อเริ่มตรวจจับรอบใหม่
                avg_frame = None

                # จัดการไฟล์เก่าใน Thread แยก
                threading.Thread(target=manage_files, daemon=True).start()

                print("[*] System Ready for next motion.")

            # ลูปเช็คภาพ 0.2 วินาที
            time.sleep(0.2)

        except Exception as e:
            print(f"[!] Error in Main Loop: {e}")
            time.sleep(2)
            restart_camera()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
        if picam2:
            picam2.stop()
            picam2.close()
