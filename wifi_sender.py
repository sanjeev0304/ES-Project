"""
WiFi Sensor Simulator (Sender)
Simulates a sensor device that sends values over TCP/WiFi.
Some values will intentionally be out of the 35-45 range to trigger alerts.
"""

import socket
import time
import random
import sys

HOST = "192.168.29.253"
PORT = 5050

def generate_sensor_value():
    """Generate a sensor value - mostly in range, occasionally out of range."""
    if random.random() < 0.25:  # 25% chance of out-of-range value
        # Generate out-of-range value
        if random.random() < 0.5:
            return round(random.uniform(20, 34.9), 2)  # Below range
        else:
            return round(random.uniform(45.1, 60), 2)   # Above range
    else:
        return round(random.uniform(35, 45), 2)  # Normal in-range value


def main():
    print("=" * 50)
    print("  WiFi SENSOR SIMULATOR (TCP Sender)")
    print("=" * 50)
    print(f"  Connecting to receiver at {HOST}:{PORT}")
    print(f"  Valid range: 35 - 45")
    print("=" * 50)

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((HOST, PORT))
            print(f"\n[CONNECTED] Sending sensor data...\n")

            count = 0
            while True:
                value = generate_sensor_value()
                count += 1
                status = "OK" if 35 <= value <= 45 else "!! OUT OF RANGE"
                message = f"{value}\n"
                sock.sendall(message.encode())
                print(f"  Sent #{count}: {value:>7.2f}  {status}")
                time.sleep(1.5)  # Send every 1.5 seconds

        except ConnectionRefusedError:
            print("[WAITING] Receiver not running. Retrying in 3s...")
            time.sleep(3)
        except BrokenPipeError:
            print("[DISCONNECTED] Receiver closed. Reconnecting in 3s...")
            time.sleep(3)
        except KeyboardInterrupt:
            print("\n[STOPPED] Sender shutting down.")
            sock.close()
            sys.exit(0)


if __name__ == "__main__":
    main()
