"""
BLE Sensor Simulator (Sender)
Simulates a BLE peripheral sending sensor values.

Since real BLE requires hardware, this uses a local Unix socket
to simulate BLE communication. The protocol mimics BLE characteristics:
- Short packets (like BLE GATT notifications)
- Periodic updates (like BLE notify interval)

For REAL BLE hardware (ESP32, Arduino, Raspberry Pi), see ble_real_device.py
"""

import socket
import time
import random
import struct
import os
import sys

BLE_SOCKET_PATH = "/tmp/ble_sensor_sim.sock"

def generate_sensor_value():
    """Generate a sensor value - mostly in range, occasionally out of range."""
    if random.random() < 0.25:
        if random.random() < 0.5:
            return round(random.uniform(20, 34.9), 2)
        else:
            return round(random.uniform(45.1, 60), 2)
    else:
        return round(random.uniform(35, 45), 2)


def create_ble_packet(value: float) -> bytes:
    """
    Create a BLE-style notification packet.
    Format: [START_BYTE][LENGTH][VALUE_FLOAT][CHECKSUM][END_BYTE]
    This mimics how real BLE GATT characteristics send data.
    """
    start = b'\xAA'
    end = b'\x55'
    payload = struct.pack('<f', value)  # Little-endian float (4 bytes)
    length = struct.pack('B', len(payload))
    checksum = struct.pack('B', sum(payload) & 0xFF)
    return start + length + payload + checksum + end


def parse_ble_packet(data: bytes):
    """Parse a BLE-style packet and extract the float value."""
    if len(data) >= 7 and data[0:1] == b'\xAA' and data[-1:] == b'\x55':
        value = struct.unpack('<f', data[2:6])[0]
        return round(value, 2)
    return None


def main():
    print("=" * 50)
    print("  BLE SENSOR SIMULATOR (Peripheral)")
    print("=" * 50)
    print(f"  Simulating BLE GATT Notifications")
    print(f"  Service UUID: 0000180d-0000-1000-8000-00805f9b34fb")
    print(f"  Char UUID:    00002a37-0000-1000-8000-00805f9b34fb")
    print(f"  Valid range: 35 - 45")
    print("=" * 50)

    # Clean up old socket
    if os.path.exists(BLE_SOCKET_PATH):
        os.remove(BLE_SOCKET_PATH)

    # Create Unix domain socket (simulates BLE)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(BLE_SOCKET_PATH)
    server.listen(1)
    print(f"\n  [BLE] Advertising... waiting for central to connect")
    print(f"  [BLE] Socket: {BLE_SOCKET_PATH}\n")

    try:
        while True:
            conn, _ = server.accept()
            print("  [BLE] Central connected! Sending notifications...\n")
            count = 0
            try:
                while True:
                    value = generate_sensor_value()
                    count += 1
                    packet = create_ble_packet(value)
                    conn.sendall(packet)

                    status = "OK" if 35 <= value <= 45 else "!! OUT OF RANGE"
                    print(f"  Notify #{count}: {value:>7.2f}  [{len(packet)} bytes]  {status}")
                    time.sleep(1.5)
            except BrokenPipeError:
                print("\n  [BLE] Central disconnected.\n  [BLE] Re-advertising...\n")
    except KeyboardInterrupt:
        print("\n[STOPPED] BLE peripheral shutting down.")
        server.close()
        os.remove(BLE_SOCKET_PATH)


if __name__ == "__main__":
    main()
