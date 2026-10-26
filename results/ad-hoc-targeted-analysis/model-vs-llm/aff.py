"""Set this process's CPU affinity to 0xFF0 (keep cores 0-3 free) on Windows. Import first."""
import ctypes
import sys

if sys.platform == "win32":
    k = ctypes.windll.kernel32
    k.GetCurrentProcess.restype = ctypes.c_void_p
    ok = k.SetProcessAffinityMask(ctypes.c_void_p(k.GetCurrentProcess()), ctypes.c_size_t(0xFF0))
    if not ok:
        print("warning: affinity not set", file=sys.stderr)
