import socket, cv2, struct, time, os, threading, subprocess
import numpy as np
from picamera2 import Picamera2

# --- CONFIGURATION ---
ZERO_PORT = 8000
VIDEO_DIR = "/home/wasankds/eagle-eye-legion-pizero/videos"
MAX_FILES = 100             # จำนวนไฟล์ที่จะบันทึก
MOTION_THRESHOLD = 5000     # เพิ่มค่านี้ถ้ามันบันทึกบ่อยเกินไป
RECORD_DURATION = 15        # บันทึก 15 วินาที
STREAM_TO_SERVER_SECONDS = 0.2 # หรือ 5 FPS

if not os.path.exists(VIDEO_DIR):
    os.makedirs(VIDEO_DIR)

# --- GLOBAL VARIABLES ---
current_frame = None
is_recording = False
picam2 = None

def manage_files():
    """จัดการจำนวนไฟล์ในเครื่อง"""
    files = sorted([os.path.join(VIDEO_DIR, f) for f in os.listdir(VIDEO_DIR) if f.endswith('.h264')])
    while len(files) >= MAX_FILES:
        try:
            os.remove(files[0])
            files.pop(0)
        except: break

def recording_task_system():
    """บันทึกวิดีโอด้วย rpicam-vid แบบ Low Resource"""
    global is_recording, picam2
    is_recording = True
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    h264_path = f"{VIDEO_DIR}/motion_{timestamp}.h264"
    
    print(f"[!] Motion Detected! Recording (10fps) to {h264_path}...")
    
    try:
        # ปิดกล้องใน Python เพื่อคืนแรมและทรัพยากรให้ระบบ
        if picam2:
            picam2.stop()
            picam2.close()
            picam2 = None
        
        # ปรับจูน: 640x480, 10fps, 1.5Mbps ช่วยให้ Pi Zero 2 W ไม่ค้าง
        cmd = (f"rpicam-vid --nopreview -t {RECORD_DURATION * 1000} "
               f"--width 640 --height 480 --framerate 10 --bitrate 1500000 "
               f"-o {h264_path}")
        
        subprocess.run(cmd, shell=True)
        
        print(f"[*] Finished: {h264_path}")
        manage_files()
    except Exception as e:
        print(f"[!] Recording Error: {e}")
    
    # กลับมาเริ่มการตรวจจับใหม่
    print("[*] Restarting Monitoring...")
    start_camera()
    is_recording = False


def motion_detection():
    """ตรวจจับการเคลื่อนไหวแบบประหยัด CPU"""
    global is_recording, current_frame
    avg_frame = None
    while True:
        # ตรวจจับเฉพาะตอนที่ไม่ได้บันทึกวิดีโออยู่
        if not is_recording and current_frame is not None:
            frame = current_frame.copy()
            # ย่อภาพให้เล็กลงมาก (80x60) เพื่อประหยัด RAM ในการวิเคราะห์
            small_frame = cv2.resize(frame, (80, 60))
            gray = cv2.cvtColor(small_frame, cv2.COLOR_RGB2GRAY)
            gray = cv2.GaussianBlur(gray, (25, 25), 0)
            
            if avg_frame is None:
                avg_frame = gray.copy().astype("float")
                continue
            
            cv2.accumulateWeighted(gray, avg_frame, 0.5)
            frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(avg_frame))
            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
            
            if np.sum(thresh) > MOTION_THRESHOLD:
                threading.Thread(target=recording_task_system, daemon=True).start()
        
        # พัก 1 วินาที เพื่อไม่ให้ CPU ร้อนเกินไป
        time.sleep(1.0)


def stream_to_pi5():
    """สตรีมภาพ JPEG ไปยังเครื่องรับ"""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', ZERO_PORT))
    server_sock.listen(1)
    
    while True:
        conn, addr = server_sock.accept()
        try:
            while True:
                # หยุดส่งสตรีมชั่วคราวขณะบันทึกวิดีโอเพื่อประหยัดทรัพยากร
                if current_frame is not None and not is_recording:
                    _, data = cv2.imencode('.jpg', current_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                    msg = data.tobytes()
                    conn.sendall(struct.pack("<L", len(msg)) + msg)
                time.sleep(STREAM_TO_SERVER_SECONDS)
        except: pass
        finally: conn.close()


def start_camera():
    """เริ่มต้นกล้องใหม่"""
    global picam2
    try:
        picam2 = Picamera2()
        config = picam2.create_video_configuration()
        config['main'] = {"format": "RGB888", "size": (640, 480)}
        picam2.configure(config)
        picam2.start()
    except Exception as e:
        print(f"[!] Camera Start Error: {e}")


def main_loop():
    """Loop หลักสำหรับดึงภาพจากกล้อง"""
    global current_frame
    start_camera()
    print("[*] System Ready. Monitoring for motion...")
    
    # รัน Motion Detection ใน Thread แยก
    threading.Thread(target=motion_detection, daemon=True).start()
    
    while True:
        if not is_recording and picam2 is not None:
            try:
                current_frame = picam2.capture_array()
            except: 
                pass
        time.sleep(0.05) # ลดความถี่การดึงภาพลงเล็กน้อย



if __name__ == "__main__":
    try:
        # รัน Thread สตรีมภาพ
        threading.Thread(target=stream_to_pi5, daemon=True).start()

        # รัน Loop หลัก
        main_loop()
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
    finally:
        if picam2:
            picam2.close()
