"""
BLE Sensor Receiver + Alert System
- Connects to BLE peripheral (simulated via Unix socket)
- Parses BLE GATT-style notification packets
- Maintains a sliding window of 10 values
- Serves a live web UI dashboard with alerts
"""

import socket
import struct
import threading
import json
import time
import asyncio
import websockets
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

# ─── Configuration ────────────────────────────────────────
BLE_SOCKET_PATH = "/tmp/ble_sensor_sim.sock"
WS_PORT = 8765
HTTP_PORT = 8080
VALID_MIN = 35
VALID_MAX = 45
WINDOW_SIZE = 10

# ─── Shared State ─────────────────────────────────────────
sensor_window = []
all_values = []
alerts = []
ws_clients = set()
lock = threading.Lock()


def parse_ble_packet(data: bytes):
    """Parse a BLE-style notification packet."""
    if len(data) >= 7 and data[0:1] == b'\xAA' and data[-1:] == b'\x55':
        value = struct.unpack('<f', data[2:6])[0]
        return round(value, 2)
    return None


def process_value(value: float):
    """Process a new sensor value: update window, check alerts."""
    with lock:
        timestamp = time.strftime("%H:%M:%S")
        entry = {
            "value": value,
            "time": timestamp,
            "in_range": VALID_MIN <= value <= VALID_MAX
        }

        all_values.append(entry)
        sensor_window.append(entry)

        if len(sensor_window) > WINDOW_SIZE:
            sensor_window.pop(0)

        out_of_range = [v for v in sensor_window if not v["in_range"]]
        window_has_alert = len(out_of_range) > 0

        if not entry["in_range"]:
            alert_msg = f"ALERT at {timestamp}: Value {value} is OUT OF RANGE [{VALID_MIN}-{VALID_MAX}]"
            alerts.append({"message": alert_msg, "time": timestamp, "value": value})
            print(f"  🚨 {alert_msg}")
        else:
            print(f"  ✅ {timestamp}: Value {value:.2f} - OK")

        payload = {
            "type": "update",
            "window": list(sensor_window),
            "latest": entry,
            "window_has_alert": window_has_alert,
            "out_of_range_count": len(out_of_range),
            "total_received": len(all_values),
            "alerts": alerts[-10:],
            "connection": "BLE"
        }

    asyncio.run_coroutine_threadsafe(broadcast(json.dumps(payload)), ws_loop)


async def broadcast(message):
    if ws_clients:
        await asyncio.gather(
            *[client.send(message) for client in ws_clients],
            return_exceptions=True
        )


async def ws_handler(websocket):
    ws_clients.add(websocket)
    print(f"  [WS] Browser connected ({len(ws_clients)} clients)")
    try:
        with lock:
            payload = {
                "type": "update",
                "window": list(sensor_window),
                "latest": sensor_window[-1] if sensor_window else None,
                "window_has_alert": any(not v["in_range"] for v in sensor_window),
                "out_of_range_count": sum(1 for v in sensor_window if not v["in_range"]),
                "total_received": len(all_values),
                "alerts": alerts[-10:],
                "connection": "BLE"
            }
        await websocket.send(json.dumps(payload))
        async for _ in websocket:
            pass
    finally:
        ws_clients.discard(websocket)


def run_ws_server():
    global ws_loop
    ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws_loop)
    start_server = websockets.serve(ws_handler, "0.0.0.0", WS_PORT)
    ws_loop.run_until_complete(start_server)
    ws_loop.run_forever()


def run_ble_client():
    """Connect to BLE peripheral (simulated) and receive notifications."""
    print(f"  [BLE] Scanning for peripheral...")

    while True:
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(BLE_SOCKET_PATH)
            print(f"  [BLE] Connected to peripheral!")
            print(f"  [BLE] Subscribing to GATT notifications...\n")

            while True:
                data = sock.recv(7)  # BLE packet is 7 bytes
                if not data:
                    break
                value = parse_ble_packet(data)
                if value is not None:
                    process_value(value)

        except (ConnectionRefusedError, FileNotFoundError):
            print("  [BLE] Peripheral not found. Scanning again in 3s...")
            time.sleep(3)
        except ConnectionResetError:
            print("  [BLE] Peripheral disconnected. Re-scanning...")
            time.sleep(3)


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
            with open(html_path, "r") as f:
                content = f.read()
                # Inject BLE connection type
                content = content.replace(
                    'let connectionType = "WiFi"',
                    'let connectionType = "BLE"'
                )
                self.wfile.write(content.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def run_http_server():
    server = HTTPServer(("0.0.0.0", HTTP_PORT), DashboardHandler)
    print(f"  [HTTP] Dashboard at http://localhost:{HTTP_PORT}")
    server.serve_forever()


def main():
    print("=" * 50)
    print("  BLE SENSOR RECEIVER + ALERT SYSTEM")
    print("=" * 50)
    print(f"  Simulating BLE Central (GATT Client)")
    print(f"  Valid range: {VALID_MIN} - {VALID_MAX}")
    print(f"  Window size: {WINDOW_SIZE} values")
    print("=" * 50)

    threading.Thread(target=run_ws_server, daemon=True).start()
    time.sleep(0.5)
    threading.Thread(target=run_http_server, daemon=True).start()
    threading.Thread(target=run_ble_client, daemon=True).start()

    print(f"\n  📡 Open http://localhost:{HTTP_PORT} in your browser")
    print(f"  📡 Then run: python ble_sender.py\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[STOPPED] BLE receiver shutting down.")


if __name__ == "__main__":
    main()
