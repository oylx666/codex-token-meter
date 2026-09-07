"""Login companion: launch meter on Codex desktop start, no model/network calls."""
import ctypes
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from common import STATE_DIR, marker, signal
from settings import read_settings


def desktop_window_count(pids):
    """Visible top-level windows count; minimized windows remain visible to Win32."""
    if not pids:
        return 0
    user = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    user.EnumWindows.argtypes = [callback_type, w.LPARAM]
    user.IsWindowVisible.argtypes = [w.HWND]
    user.GetWindowTextLengthW.argtypes = [w.HWND]
    user.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
    matches=[]
    @callback_type
    def visit(hwnd, _):
        pid=w.DWORD()
        user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        if pid.value in pids and user.IsWindowVisible(hwnd) and user.GetWindowTextLengthW(hwnd)>0:
            matches.append(hwnd)
        return True
    if not user.EnumWindows(visit,0):
        raise ctypes.WinError(ctypes.get_last_error())
    return len(matches)


def is_codex_desktop(path):
    path = path.replace('/', '\\').lower()
    return Path(path).name.lower() in ('chatgpt.exe', 'codex.exe') and ('\\openai.codex_' in path or '\\codex\\app\\' in path)


def codex_desktop_pids():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    class Entry(ctypes.Structure):
        _fields_ = [('dwSize', w.DWORD), ('cntUsage', w.DWORD), ('th32ProcessID', w.DWORD),
                    ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', w.DWORD),
                    ('cntThreads', w.DWORD), ('th32ParentProcessID', w.DWORD),
                    ('pcPriClassBase', w.LONG), ('dwFlags', w.DWORD), ('szExeFile', w.WCHAR * 260)]
    kernel.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = w.HANDLE
    kernel.Process32FirstW.argtypes = [w.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes = [w.HANDLE, ctypes.POINTER(Entry)]
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    result = []
    try:
        entry = Entry()
        entry.dwSize = ctypes.sizeof(entry)
        more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            if entry.szExeFile.lower() in ('chatgpt.exe', 'codex.exe'):
                handle = kernel.OpenProcess(0x1000, False, entry.th32ProcessID)
                if handle:
                    try:
                        buffer = ctypes.create_unicode_buffer(32768)
                        size = w.DWORD(len(buffer))
                        if kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                            path = buffer.value.lower()
                            if is_codex_desktop(path):
                                result.append(entry.th32ProcessID)
                    finally:
                        kernel.CloseHandle(handle)
            more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    return result


class Lifecycle:
    def __init__(self):
        self.present = False
        self.absent_checks = 0
        self.previous_auto_open = False

    def update(self, present, auto_open=True, auto_close=True):
        enabled_now = auto_open and not self.previous_auto_open
        self.previous_auto_open = auto_open
        if present:
            self.absent_checks = 0
            if not self.present:
                self.present = True
                return 'start' if auto_open else None
            if enabled_now:
                return 'start'
        elif self.present:
            self.absent_checks += 1
            if self.absent_checks >= 2:
                self.present = False
                return 'stop' if auto_close else None
        return None


def request_meter_close():
    signal('close-request')


def main():
    if '--probe' in sys.argv:
        pids=codex_desktop_pids()
        print(json.dumps(dict(codex_desktop_pids=pids,desktop_windows=desktop_window_count(pids),settings=read_settings())))
        return
    from singleton import acquire
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    instance_mutex = acquire('watcher')
    if instance_mutex is None:
        return
    (STATE_DIR / 'watcher.pid').write_text(str(os.getpid()), encoding='ascii')
    lifecycle = Lifecycle()
    windowless = Path(sys.executable).with_name('pythonw.exe')
    stop_at_start = marker('stop-watcher')
    while True:
        stop_stamp = marker('stop-watcher')
        if stop_stamp and stop_stamp != stop_at_start:
            break
        action = None
        try:
            settings=read_settings()
            action = lifecycle.update(bool(desktop_window_count(codex_desktop_pids())), **settings)
            if action == 'start':
                subprocess.Popen([str(windowless), str(Path(__file__).with_name('meter.py'))], creationflags=subprocess.CREATE_NO_WINDOW)
            elif action == 'stop':
                request_meter_close()
        except Exception as exc:
            if action == 'start':
                lifecycle.present = False  # Retry a failed launch on the next poll.
            try:
                (STATE_DIR / 'watcher-error.txt').write_text(type(exc).__name__ + ': ' + str(exc), encoding='utf-8')
            except OSError:
                pass
        time.sleep(3)
    (STATE_DIR / 'watcher.pid').unlink(missing_ok=True)


if __name__ == '__main__':
    main()
