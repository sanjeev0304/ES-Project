"""
WiFi Sensor Receiver + Alert System
- Receives sensor values over TCP (WiFi simulation)
- Maintains a sliding window of 10 values
- Serves a live web UI dashboard with alerts
- WebSocket pushes real-time updates to the browser
"""

import socket
import threading
import json
import time
import asyncio
import websockets
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

# ─── Configuration ────────────────────────────────────────
TCP_HOST = "0.0.0.0"
TCP_PORT = 5050
WS_PORT = 8765
HTTP_PORT = 8080
VALID_MIN = 35
VALID_MAX = 45
WINDOW_SIZE = 10

# ─── Shared State ─────────────────────────────────────────
sensor_window = []       # Sliding window of last 10 values
all_values = []          # Full history
alerts = []              # Alert log
ws_clients = set()       # Connected WebSocket clients
lock = threading.Lock()


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

        # Keep only the last WINDOW_SIZE values in the window
        if len(sensor_window) > WINDOW_SIZE:
            sensor_window.pop(0)

        # Check if any value in current window is out of range
        out_of_range = [v for v in sensor_window if not v["in_range"]]
        window_has_alert = len(out_of_range) > 0

        if not entry["in_range"]:
            alert_msg = f"ALERT at {timestamp}: Value {value} is OUT OF RANGE [{VALID_MIN}-{VALID_MAX}]"
            alerts.append({"message": alert_msg, "time": timestamp, "value": value})
            print(f"  🚨 {alert_msg}")
        else:
            print(f"  ✅ {timestamp}: Value {value:.2f} - OK")

        # Build payload for UI
        payload = {
            "type": "update",
            "window": list(sensor_window),
            "latest": entry,
            "window_has_alert": window_has_alert,
            "out_of_range_count": len(out_of_range),
            "total_received": len(all_values),
            "alerts": alerts[-10:]  # Last 10 alerts
        }

    # Push to all WebSocket clients
    asyncio.run_coroutine_threadsafe(broadcast(json.dumps(payload)), ws_loop)


async def broadcast(message):
    """Send message to all connected WebSocket clients."""
    if ws_clients:
        await asyncio.gather(
            *[client.send(message) for client in ws_clients],
            return_exceptions=True
        )


async def ws_handler(websocket):
    """Handle WebSocket connections from the browser UI."""
    ws_clients.add(websocket)
    print(f"  [WS] Browser connected ({len(ws_clients)} clients)")
    try:
        # Send current state immediately
        with lock:
            payload = {
                "type": "update",
                "window": list(sensor_window),
                "latest": sensor_window[-1] if sensor_window else None,
                "window_has_alert": any(not v["in_range"] for v in sensor_window),
                "out_of_range_count": sum(1 for v in sensor_window if not v["in_range"]),
                "total_received": len(all_values),
                "alerts": alerts[-10:]
            }
        await websocket.send(json.dumps(payload))
        async for _ in websocket:
            pass  # Keep alive
    finally:
        ws_clients.discard(websocket)
        print(f"  [WS] Browser disconnected ({len(ws_clients)} clients)")


def run_ws_server():
    """Run the WebSocket server in its own thread."""
    global ws_loop
    ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws_loop)

    async def _serve():
        async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
            await asyncio.Future()  # run forever

    ws_loop.run_until_complete(_serve())


def run_tcp_server():
    """TCP server that receives sensor values from the sender."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((TCP_HOST, TCP_PORT))
    server.listen(1)
    print(f"  [TCP] Listening on {TCP_HOST}:{TCP_PORT}")

    while True:
        conn, addr = server.accept()
        print(f"  [TCP] Sensor connected from {addr}")
        buffer = ""
        try:
            while True:
                data = conn.recv(1024).decode()
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        try:
                            value = float(line)
                            process_value(value)
                        except ValueError:
                            print(f"  [TCP] Invalid data: {line}")
        except ConnectionResetError:
            print(f"  [TCP] Sensor disconnected")


class DashboardHandler(SimpleHTTPRequestHandler):
    """Serve the HTML dashboard."""
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            # Read the dashboard HTML file
            html_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
            with open(html_path, "r") as f:
                self.wfile.write(f.read().encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress HTTP logs


def run_http_server():
    """Serve the dashboard UI."""
    class ReuseHTTPServer(HTTPServer):
        allow_reuse_address = True

    server = ReuseHTTPServer(("0.0.0.0", HTTP_PORT), DashboardHandler)
    print(f"  [HTTP] Dashboard at http://localhost:{HTTP_PORT}")
    server.serve_forever()


def main():
    print("=" * 50)
    print("  WiFi SENSOR RECEIVER + ALERT SYSTEM")
    print("=" * 50)
    print(f"  Valid range: {VALID_MIN} - {VALID_MAX}")
    print(f"  Window size: {WINDOW_SIZE} values")
    print("=" * 50)

    # Start all servers in separate threads
    threading.Thread(target=run_ws_server, daemon=True).start()
    time.sleep(0.5)
    threading.Thread(target=run_http_server, daemon=True).start()
    threading.Thread(target=run_tcp_server, daemon=True).start()

    print(f"\n  📡 Open http://localhost:{HTTP_PORT} in your browser")
    print(f"  📡 Then run: python wifi_sender.py\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[STOPPED] Receiver shutting down.")


if __name__ == "__main__":
    main()
