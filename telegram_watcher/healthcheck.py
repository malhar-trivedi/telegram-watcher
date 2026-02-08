import os
import sys
import time

HEARTBEAT_FILE = "/tmp/heartbeat"
MAX_DELAY_SECONDS = 120  # 2 minutes tolerance

def check_health():
    if not os.path.exists(HEARTBEAT_FILE):
        print(f"Error: Heartbeat file {HEARTBEAT_FILE} not found.")
        sys.exit(1)

    try:
        mtime = os.path.getmtime(HEARTBEAT_FILE)
        age = time.time() - mtime

        if age > MAX_DELAY_SECONDS:
            print(f"Error: Heartbeat is stale (Last update: {age:.1f}s ago).")
            sys.exit(1)

        print(f"Healthy: Heartbeat updated {age:.1f}s ago.")
        sys.exit(0)

    except Exception as e:
        print(f"Error checking health: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_health()
