"""
publisher.py
------------
Simulates an IoT device (e.g. an ESP32 with a temperature/humidity/motion
sensor) that periodically reads sensor values and sends them to the
dashboard service.

NOTE ON THIS VERSION: this sends data via a direct HTTP POST to
dashboard.py running on the same machine (http://127.0.0.1:5000).
The original design used MQTT to a public broker (broker.hivemq.com),
which is how a real IoT deployment works -- but that requires an
outbound internet connection on ports 1883/8883, which got blocked by
network/firewall/antivirus software during testing. This local HTTP
version removes that dependency entirely so the pipeline works
reliably on any machine, while keeping the same overall shape:
device -> ingestion endpoint -> stored readings -> dashboard.

Run dashboard.py FIRST, then run this file in a separate terminal.
"""

import random
import time
from datetime import datetime, timezone

import requests

DASHBOARD_URL = "http://127.0.0.1:5000/api/ingest"
DEVICE_ID = "sim-device-01"
PUBLISH_INTERVAL_SECONDS = 3


def generate_reading():
    """
    Fakes one sensor reading. In a real device, these lines would instead
    read actual ADC/GPIO values from a temperature/humidity/PIR sensor.
    """
    return {
        "device_id": DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_c": round(random.uniform(20.0, 45.0), 2),
        "humidity_pct": round(random.uniform(30.0, 90.0), 2),
        "motion_detected": random.random() < 0.15,  # ~15% chance per reading
    }


def main():
    print(f"Sending simulated sensor data to {DASHBOARD_URL} "
          f"every {PUBLISH_INTERVAL_SECONDS}s. Press Ctrl+C to stop.\n")
    print("Make sure dashboard.py is already running in another terminal!\n")

    try:
        while True:
            reading = generate_reading()
            try:
                response = requests.post(DASHBOARD_URL, json=reading, timeout=5)
                if response.status_code == 200:
                    print(f"Sent: {reading}")
                else:
                    print(f"Dashboard responded with status "
                          f"{response.status_code}: {response.text}")
            except requests.exceptions.ConnectionError:
                print("Could not reach dashboard.py -- "
                      "is it running at http://127.0.0.1:5000 ?")
            time.sleep(PUBLISH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopping publisher.")


if __name__ == "__main__":
    main()

