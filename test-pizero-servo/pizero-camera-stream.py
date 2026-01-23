import socket
import cv2
import struct
import time
from picamera2 import Picamera2
from libcamera import Transform

# --- CONFIGURATION ---
CONFIG = {
    "port": 8000,
    "width": 640,
    "height": 480,
    "fps": 20,
    "quality": 60,
    "format": "RGB888",
    # กำหนดค่าหมุนตรงนี้ hflip=True, vflip=True คือหมุน 180
    "transform": Transform(hflip=True, vflip=True)
}


def start_slave_camera():
    picam2 = Picamera2()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', CONFIG["port"]))
    server_sock.listen(1)

    print(f"=== Pi Zero Camera Node Ready on Port {CONFIG['port']} ===")
    frame_delay = 1.0 / CONFIG["fps"]

    try:
        while True:
            conn, addr = server_sock.accept()
            print(f"Connected by {addr}")

            try:
                # วิธีที่ 1: ส่ง transform เข้าไปตั้งแต่ตอนสร้าง Config (ถ้าเวอร์ชันรองรับ)
                camera_config = picam2.create_video_configuration(
                    main={"format": CONFIG["format"], "size": (
                        CONFIG["width"], CONFIG["height"])},
                    transform=CONFIG["transform"]
                )

                # วิธีที่ 2: ถ้าวิธีแรกไม่ทำงาน ให้ลองยัดเข้า Dictionary ตรงๆ
                # ตรวจสอบว่าเป็น dict หรือไม่ ถ้าใช่ให้ใช้การกำหนดค่าแบบ key
                if isinstance(camera_config, dict):
                    camera_config["transform"] = CONFIG["transform"]
                else:
                    # ถ้าเป็นวัตถุ (Object) ให้ใช้ property
                    camera_config.transform = CONFIG["transform"]

                picam2.configure(camera_config)
                picam2.start()

                print("Streaming started (Rotation Applied)...")

                while True:
                    frame = picam2.capture_array()

                    _, data = cv2.imencode(
                        '.jpg', frame, [
                            int(cv2.IMWRITE_JPEG_QUALITY), CONFIG["quality"]]
                    )
                    msg = data.tobytes()

                    header = struct.pack("<L", len(msg))
                    conn.sendall(header + msg)

                    time.sleep(frame_delay)

            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                print("Client disconnected.")
            except Exception as e:
                print(f"Loop Error: {e}")
            finally:
                picam2.stop()
                conn.close()
                print("Standby...")

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server_sock.close()


if __name__ == "__main__":
    start_slave_camera()
