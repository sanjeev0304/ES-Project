# ES-Project
# 📡 Sensor Alert System

A real-time sensor monitoring system that receives numerical values over **WiFi (TCP/IP)** or **BLE (Bluetooth Low Energy)** and triggers alerts when any value in a sliding window of 10 falls outside the valid range of **35–45**.

Built in pure Python with a live browser-based dashboard powered by WebSockets.

---

## 📸 Demo

```
Sensor Device  ──── WiFi (TCP) / BLE ────▶  Python Receiver  ──── WebSocket ────▶  Browser Dashboard
  (Sender)                                   (Alert Engine)                          (Live UI + Alerts)
```

The dashboard shows:
- A **5×2 grid** of the current window (green = in range, red = out of range)
- A **flashing alert banner** when any value in the window is out of range
- A **live line chart** with the valid range band highlighted
- A **range indicator bar** showing where the latest value falls
- A **timestamped alert log** of every out-of-range event

---

## 🗂 Project Structure

```
sensor-alert-system/
│
├── main.py              # Interactive launcher — choose WiFi or BLE
│
├── wifi_sender.py       # Simulates a sensor device sending values over TCP/WiFi
├── wifi_receiver.py     # TCP server + alert engine + WebSocket + HTTP dashboard server
│
├── ble_sender.py        # Simulates a BLE peripheral sending GATT notification packets
├── ble_receiver.py      # BLE central + alert engine + WebSocket + HTTP dashboard server
│
└── dashboard.html       # Browser UI — live updates via WebSocket, no framework needed
```

---

## ⚙️ How It Works

### 1. Connection Layer

**WiFi Mode (TCP/IP)**

The sender opens a TCP socket and connects to the receiver's IP and port. Values are sent as newline-delimited UTF-8 strings (e.g. `"37.52\n"`). The receiver binds a server socket, accepts the connection, and reads the stream.

```
Sender                          Receiver (0.0.0.0:5050)
  │   socket.connect(IP, 5050)      │
  │ ──── TCP Handshake ───────────▶ │  server.accept()
  │   sendall("37.52\n")            │
  │ ──── bytes ───────────────────▶ │  recv() → float("37.52") → 37.52
```

**BLE Mode (Simulated GATT)**

The BLE sender acts as a **peripheral** and the receiver acts as a **central**. Communication uses a Unix domain socket locally to simulate the Bluetooth transport layer. Data is sent as structured binary packets that mimic real BLE GATT characteristic notifications:

```
Byte 0     : Start byte       0xAA
Byte 1     : Payload length   0x04
Bytes 2–5  : Float value      little-endian IEEE 754 (4 bytes)
Byte 6     : Checksum         sum of payload bytes & 0xFF
Byte 7     : End byte         0x55
```

This mimics real BLE GATT notification packets as used with actual hardware (ESP32, Arduino, etc.).

### 2. Alert Engine

Every received value is processed by the alert engine:

1. Value is added to a **sliding window** (max 10 entries)
2. If the window exceeds 10, the oldest entry is dropped
3. The entire window is scanned — if **any value** is outside `[35, 45]`, an alert is raised
4. The alert is timestamped and appended to the alert log
5. The updated state is broadcast to all connected browser clients via WebSocket

### 3. Dashboard (Browser UI)

The receiver serves `dashboard.html` over HTTP (port 8080) and maintains a WebSocket server (port 8765). The browser connects to the WebSocket and receives JSON payloads on every new value. The UI updates the window grid, chart, banner, and alert log in real time — no page refresh needed.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Both devices on the **same WiFi network** (for cross-device WiFi mode)

### Install Dependencies

```bash
pip install websockets
```

That's the only external dependency. Everything else (`socket`, `threading`, `asyncio`, `struct`, `http.server`) is Python standard library.

### Run (Interactive)

```bash
python main.py
```

Choose **1** for WiFi or **2** for BLE, then follow the prompts.

### Run Manually

**WiFi Mode — same machine:**

```bash
# Terminal 1
python wifi_receiver.py

# Terminal 2
python wifi_sender.py

# Browser
open http://localhost:8080
```

**WiFi Mode — two machines on the same network:**

```bash
# On the RECEIVER machine — find its IP first
ipconfig getifaddr en0        # Mac
hostname -I                   # Linux
ipconfig                      # Windows (look for IPv4 under Wi-Fi)

# Then on the RECEIVER machine
python wifi_receiver.py

# On the SENDER machine — edit wifi_sender.py first:
# HOST = "192.168.x.x"   ← replace with receiver's IP
python wifi_sender.py

# Browser (on any machine on the network)
open http://<receiver-ip>:8080
```

**BLE Mode:**

```bash
# Terminal 1 — start peripheral first
python ble_sender.py

# Terminal 2 — start central
python ble_receiver.py

# Browser
open http://localhost:8080
```

---

## 📦 Python Libraries Used

### External (install via pip)

| Library | Version | Purpose |
|---|---|---|
| `websockets` | ≥ 14.x | WebSocket server for real-time browser updates |

### Standard Library (no install needed)

| Module | Purpose |
|---|---|
| `socket` | TCP server/client (WiFi) and Unix domain socket (BLE simulation) |
| `threading` | Runs TCP, WebSocket, and HTTP servers concurrently |
| `asyncio` | Async event loop for the WebSocket server |
| `struct` | Packs/unpacks binary BLE GATT-style packets (`<f` little-endian float) |
| `json` | Serializes state payloads sent to the browser |
| `http.server` | Serves the dashboard HTML over HTTP |
| `time` | Timestamps for alerts and value entries |
| `random` | Generates simulated sensor values (25% chance of out-of-range) |
| `os` | File path resolution for `dashboard.html` |
| `sys` | Clean exit on `KeyboardInterrupt` |
| `subprocess` | `main.py` launches receiver scripts as subprocesses |

---

## 🔧 Configuration

All key parameters are at the top of each receiver file:

```python
TCP_HOST    = "0.0.0.0"   # Listen on all interfaces
TCP_PORT    = 5050         # TCP port for sensor data
WS_PORT     = 8765         # WebSocket port for browser
HTTP_PORT   = 8080         # HTTP port for dashboard
VALID_MIN   = 35           # Lower bound of valid range
VALID_MAX   = 45           # Upper bound of valid range
WINDOW_SIZE = 10           # Sliding window size
```

---

## 🔌 Ports Used

| Port | Protocol | Purpose |
|---|---|---|
| `5050` | TCP | Sensor data stream (WiFi mode) |
| `8080` | HTTP | Dashboard web UI |
| `8765` | WebSocket | Real-time browser updates |

If you see `Address already in use`, kill the previous process first:

```bash
lsof -ti:5050,8080,8765 | xargs kill -9
```

---

## 🛜 Real BLE Hardware

The BLE sender/receiver simulate Bluetooth using local Unix sockets for portability. The packet format is authentic BLE GATT. To use real hardware:

**With a real BLE device (ESP32 / Arduino)**, replace the Unix socket connection in `ble_receiver.py` with the `bleak` library:

```python
from bleak import BleakClient

DEVICE_ADDRESS = "XX:XX:XX:XX:XX:XX"   # your device's MAC
CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

async def run():
    async with BleakClient(DEVICE_ADDRESS) as client:
        await client.start_notify(CHAR_UUID, notification_handler)
        await asyncio.Future()  # run forever

def notification_handler(sender, data: bytearray):
    value = parse_ble_packet(bytes(data))
    if value is not None:
        process_value(value)
```

**With a phone as BLE peripheral**, use a free BLE peripheral simulator app (e.g. *nRF Connect* on Android/iOS) and configure it to broadcast float values on any characteristic.

---

## 🏗 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        SENDER MACHINE                           │
│                                                                 │
│  wifi_sender.py / ble_sender.py                                 │
│  ┌──────────────────────────────────┐                           │
│  │  generate_sensor_value()         │                           │
│  │  → random float, 35–60 range     │                           │
│  │  → 25% chance out-of-range       │                           │
│  │                                  │                           │
│  │  WiFi: sendall("37.52\n")        │                           │
│  │  BLE:  send(binary_packet)       │                           │
│  └──────────────┬───────────────────┘                           │
└─────────────────┼───────────────────────────────────────────────┘
                  │  WiFi: TCP port 5050
                  │  BLE:  Unix socket / Bluetooth
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                       RECEIVER MACHINE                          │
│                                                                 │
│  wifi_receiver.py / ble_receiver.py                             │
│                                                                 │
│  Thread 1: TCP / BLE listener                                   │
│  ┌──────────────────────────────────┐                           │
│  │  recv() → parse → process_value()│                           │
│  │  sliding window (max 10)         │                           │
│  │  range check [35, 45]            │                           │
│  │  build alert log                 │                           │
│  └──────────────┬───────────────────┘                           │
│                 │ run_coroutine_threadsafe()                     │
│                 ▼                                               │
│  Thread 2: WebSocket server (port 8765)                         │
│  ┌──────────────────────────────────┐                           │
│  │  broadcast(json_payload)         │──────────────────────────▶│
│  │  → all connected browsers        │    WebSocket              │
│  └──────────────────────────────────┘                           │
│                                                                 │
│  Thread 3: HTTP server (port 8080)                              │
│  ┌──────────────────────────────────┐                           │
│  │  serves dashboard.html           │                           │
│  └──────────────────────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
                  │  WebSocket ws://receiver-ip:8765
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BROWSER (any device on network)              │
│                                                                 │
│  dashboard.html                                                 │
│  ┌──────────────────────────────────┐                           │
│  │  WebSocket client                │                           │
│  │  → updateWindowGrid()            │                           │
│  │  → updateChart()                 │                           │
│  │  → updateAlertBanner()           │                           │
│  │  → updateAlertLog()              │                           │
│  └──────────────────────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📄 License

MIT — free to use, modify, and distribute.
