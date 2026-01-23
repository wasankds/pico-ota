import socket
from gpiozero import DigitalOutputDevice
import sys

# --- CONFIGURATION ---
CMD_PORT = 8001
# เก็บ Object ของพินที่เคยถูกเรียกใช้ เพื่อไม่ให้สร้างซ้ำซ้อน
active_pins = {}


def get_pin_device(pin_num):
    if pin_num not in active_pins:
        try:
            active_pins[pin_num] = DigitalOutputDevice(pin_num)
            print(f"[*] Initialized GPIO Pin: {pin_num}")
        except Exception as e:
            return None
    return active_pins[pin_num]


def start_gpio_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_sock.bind(('0.0.0.0', CMD_PORT))
        server_sock.listen(5)
        print(f"[*] Advanced GPIO Server started on port {CMD_PORT}")
    except Exception as e:
        print(f"[!] Bind failed: {e}")
        sys.exit(1)

    while True:
        conn, addr = server_sock.accept()
        try:
            while True:
                data = conn.recv(1024).decode('utf-8').strip().lower()
                if not data:
                    break

                # คาดหวังรูปแบบ: "pin:14,status:1"
                try:
                    parts = dict(item.split(":") for item in data.split(","))
                    pin_num = int(parts.get("pin"))
                    status = int(parts.get("status"))

                    device = get_pin_device(pin_num)
                    if device:
                        if status == 1:
                            device.on()
                        else:
                            device.off()
                        response = f"SUCCESS: Pin {pin_num} is {'ON' if status == 1 else 'OFF'}"
                    else:
                        response = f"ERROR: Cannot initialize Pin {pin_num}"
                except:
                    response = "ERROR: Invalid Format (Use pin:X,status:Y)"

                print(f"[CMD] {data} -> {response}")
                conn.sendall(response.encode('utf-8') + b"\n")
        except:
            pass
        finally:
            conn.close()


if __name__ == "__main__":
    start_gpio_server()
