"""
Sensor Alert System - Main Launcher
Lets the user choose WiFi or BLE connection mode.
"""

import subprocess
import sys
import os

def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║       SENSOR ALERT SYSTEM - LAUNCHER            ║")
    print("║                                                  ║")
    print("║   Monitors sensor values in range [35 - 45]      ║")
    print("║   Alerts on any out-of-range value in window     ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    print("  Choose connection type:")
    print()
    print("    [1]  WiFi  (TCP/IP connection)")
    print("    [2]  BLE   (Bluetooth Low Energy simulation)")
    print()

    choice = input("  Enter choice (1 or 2): ").strip()

    if choice == "1":
        print()
        print("  ─── WiFi Mode Selected ───")
        print()
        print("  STEP 1: This will start the RECEIVER (server + dashboard)")
        print("  STEP 2: Open a NEW terminal and run:")
        print(f"          python {os.path.join(os.path.dirname(__file__), 'wifi_sender.py')}")
        print()
        print("  STEP 3: Open http://localhost:8080 in your browser")
        print()
        input("  Press Enter to start the receiver...")
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "wifi_receiver.py")])

    elif choice == "2":
        print()
        print("  ─── BLE Mode Selected ───")
        print()
        print("  STEP 1: Open a NEW terminal and start the BLE peripheral first:")
        print(f"          python {os.path.join(os.path.dirname(__file__), 'ble_sender.py')}")
        print()
        print("  STEP 2: This will start the RECEIVER (central + dashboard)")
        print()
        print("  STEP 3: Open http://localhost:8080 in your browser")
        print()
        input("  Press Enter to start the BLE receiver...")
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "ble_receiver.py")])

    else:
        print("  Invalid choice. Please enter 1 or 2.")
        sys.exit(1)


if __name__ == "__main__":
    main()
