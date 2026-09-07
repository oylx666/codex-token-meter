"""Windows session-local, per-user mutex held for the process lifetime."""
import ctypes
from ctypes import wintypes
import hashlib
from pathlib import Path


def acquire(role):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    user = hashlib.sha256(str(Path.home()).casefold().encode()).hexdigest()[:16]
    handle = kernel.CreateMutexW(None, False, 'Local\\CodexTokenMeter-' + user + '-' + role)
    error = ctypes.get_last_error()
    if not handle:
        raise ctypes.WinError(error)
    if error == 183:
        kernel.CloseHandle(handle)
        return None
    # The OS closes this handle on process exit. Do not wrap it in a temporary object.
    return handle
