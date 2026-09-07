"""Shared local paths and failure-tolerant state operations."""
import json
import os
from pathlib import Path
import time

STATE_DIR = Path(os.environ.get('CODEX_TOKEN_METER_STATE', str(Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'CodexTokenMeter')))
CODEX_DIR = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))


def marker(name):
    try:
        return (STATE_DIR / name).read_text(encoding='ascii')[:128]
    except (OSError, UnicodeError):
        return ''


def signal(name):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / name).write_text(str(time.time_ns()), encoding='ascii')


def read_state():
    try:
        value = json.loads((STATE_DIR / 'state.json').read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(value):
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        temp = STATE_DIR / ('state-' + str(os.getpid()) + '.tmp')
        temp.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        temp.replace(STATE_DIR / 'state.json')
        return True
    except OSError:
        return False
