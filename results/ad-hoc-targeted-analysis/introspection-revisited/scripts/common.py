"""Shared paths and helpers for the introspection-revisited analysis (Created by Claude at the prompting of the repository owner)."""
import ctypes
import os

def _find_root():
    """The project root that holds runs/ and work_scratch/ (set HK_ROOT to override)."""
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(d, "runs")) and os.path.isdir(os.path.join(d, "work_scratch")):
            return d
        d = os.path.dirname(d)
    raise RuntimeError("set HK_ROOT to the folder that holds runs/ and work_scratch/")


HK = os.environ.get("HK_ROOT") or _find_root()
WORK = HK + "/work_scratch/introspection_revisited"
RUNS = HK + "/runs"
RUNCSV = {"gptoss": HK + "/work_scratch/oss_analysis/step1/final_t2/run.csv",
          "qwen": HK + "/work_scratch/analysis_final/steps/neutral/step1/run.csv"}
TABLES = {"gptoss": HK + "/work_scratch/oss_analysis/tables_t2",
          "qwen": HK + "/work_scratch/analysis_final/tables_neutral_f3"}
INTRO = ["r2f-confidant", "r3f-public", "r2s-confidant", "r3s-public", "r4-announced"]
DSET = ["d-conflict", "d-temptation-a", "d-temptation-b", "d-placebo"]
CONTROL = "headline-chat"
REPLICATES = ["hrep-fx-chat-p1", "hrep-nx-chat-p1"]   # gpt-oss replays of the identical control prompt
ARMS = INTRO + DSET + [CONTROL] + REPLICATES


def set_affinity(mask=0xFF0):
    """Keep cores 0-3 free (analysis jobs use mask 0xFF0); children inherit the mask."""
    try:
        k = ctypes.windll.kernel32
        k.SetProcessAffinityMask(k.GetCurrentProcess(), mask)
    except Exception:
        pass
