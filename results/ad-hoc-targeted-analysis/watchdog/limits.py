"""Owner CPU rule: affinity 0xFF0, BelowNormal priority, 2 BLAS threads. Import first."""
import os
os.environ.setdefault("OMP_NUM_THREADS", "2")
try:
    import ctypes
    k = ctypes.windll.kernel32
    h = k.GetCurrentProcess()
    k.SetProcessAffinityMask(h, 0xFF0)
    k.SetPriorityClass(h, 0x00004000)  # BELOW_NORMAL_PRIORITY_CLASS
except Exception:
    pass
