"""Graceful, bounded shutdown for upgrades. Never terminate unrelated Python apps."""
import argparse
import time
from common import signal
from singleton import is_running


def stop_components(timeout=10):
    signal('stop-watcher')
    signal('close-request')
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not is_running('watcher') and not is_running('meter'):
            return True
        # A child may be starting while the first notification is written.
        # Repeat until both leases disappear so it cannot miss the shutdown.
        signal('stop-watcher')
        signal('close-request')
        time.sleep(0.2)
    return False


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--stop', action='store_true', required=True)
    parser.parse_args()
    if not stop_components():
        raise SystemExit('Existing Token Meter did not stop within 10 seconds. Close it and retry installation.')


if __name__=='__main__':
    main()
