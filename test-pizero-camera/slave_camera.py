import socket
import cv2
import struct
import time
from picamera2 import Picamera2

def start_slave_camera():
    # 1. เตรียมกล้อง (ยังไม่สั่ง start จนกว่าจะมีคน connect)
    picam2 = Picamera2()
    
    # 2. ตั้งค่า Socket Server
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # อนุญาตให้ reuse port ได้ทันทีหลังปิดโปรแกรม
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', 8000))
    server_sock.listen(1)

    print("=== Pi Zero Camera Node ===")
    print("Status: Standby. Waiting for Pi 5 to request video on port 8000...")

    try:
        while True:
            # รอการเชื่อมต่อ
            conn, addr = server_sock.accept()
            print(f"\n[+] Pi 5 connected from {addr}")
            
            try:
                # เริ่มต้นการทำงานของกล้องเมื่อมีคนเชื่อมต่อ
                print("Starting camera stream...")
                config = picam2.create_video_configuration(main={"format": "RGB888", "size": (640, 480)})
                picam2.configure(config)
                picam2.start()

                while True:
                    # ดึงเฟรมภาพ
                    frame = picam2.capture_array()
                    
                    # แปลงเป็น JPEG (คุณภาพ 60% เพื่อประหยัด Bandwidth)
                    _, data = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                    msg = data.tobytes()
                    
                    # ส่งขนาดข้อมูล (Header 4 bytes) + ตัวข้อมูลภาพ
                    # ใช้ Little-endian (<L)
                    conn.sendall(struct.pack("<L", len(msg)) + msg)
                    
                    # จำกัดความเร็วที่ ~20 FPS เพื่อไม่ให้ CPU ร้อนเกินไป
                    time.sleep(0.05)

            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                print("[-] Pi 5 disconnected.")
            except Exception as e:
                print(f"Error during streaming: {e}")
            finally:
                # หยุดกล้องและปิดการเชื่อมต่อปัจจุบัน เพื่อกลับไปรอ accept() ใหม่
                print("Stopping camera and returning to standby...")
                picam2.stop()
                conn.close()

    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server_sock.close()

if __name__ == "__main__":
    start_slave_camera()
