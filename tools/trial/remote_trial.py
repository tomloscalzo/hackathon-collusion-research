"""The part of a Modal trial that runs inside the container (C8.3). Standard library only, so it is testable without Modal.

remote_run(payload) unpacks the trial's earlier files (its cache, from a previous attempt) into a fresh directory, runs the
game command there with the server key in the environment, and returns the whole directory as a tar.gz plus the (redacted)
console output. The key comes from the Modal secret as VLLM_API_KEY and is exposed to the process only under the variable
name the jar's --api-key-env names (payload["key_env"]); it is never in the payload, never returned, and any copy of it in
the console output is replaced by ***.

payload: {"argv": [...] (the token @TRIAL_DIR@ stands for the working directory), "key_env": "COLLUSION_VLLM_KEY",
          "files_tar": bytes (tar.gz of the trial's existing files, or b""), "timeout": seconds or None}
result:  {"returncode": int, "tar": bytes, "log": str}
"""
import io
import os
import signal
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

TRIAL_DIR_TOKEN = "@TRIAL_DIR@"
SECRET_ENV = "VLLM_API_KEY"          # the key inside the Modal secret collusion-vllm-api-key
MAX_LOG = 200_000


def pack_dir(path, exclude=("console.log",)):
    """tar.gz of the regular files under path, with relative names (symlinks and the like, and the excluded names, are left out)."""
    buf = io.BytesIO()
    root = Path(path)
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for f in sorted(root.rglob("*")):
            if f.is_file() and not f.is_symlink() and f.name not in exclude:
                tar.add(str(f), arcname=f.relative_to(root).as_posix())
    return buf.getvalue()


def unpack(data, dest):
    """Extract a tar.gz made by pack_dir into dest; refuses anything but plain files inside dest."""
    if not data:
        return
    dest = Path(dest).resolve()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for m in tar.getmembers():
            target = (dest / m.name).resolve()
            if not m.isfile() or m.name.startswith("/") or ".." in Path(m.name).parts or dest not in target.parents:
                raise ValueError("unsafe member in trial archive: %r" % m.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(m) as src, open(target, "wb") as out:
                out.write(src.read())


def _kill_group(p):
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except (OSError, AttributeError):
        p.kill()


def redact_files(root, secret):
    """Replace the key by *** in any file under root that contains it (the game should never write it, but a copy must not travel home)."""
    raw = secret.encode()
    for f in Path(root).rglob("*"):
        if f.is_file() and not f.is_symlink():
            data = f.read_bytes()
            if raw in data:
                f.write_bytes(data.replace(raw, b"***"))


def remote_run(payload, workdir=None):
    work = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="trial-"))
    work.mkdir(parents=True, exist_ok=True)
    unpack(payload.get("files_tar") or b"", work)
    argv = [a.replace(TRIAL_DIR_TOKEN, str(work)) for a in payload["argv"]]
    env = dict(os.environ)
    secret = env.pop(SECRET_ENV, "")
    if payload.get("key_env"):
        if not secret:
            return {"returncode": -1, "tar": b"", "log": "the Modal secret has no %s entry (or it is empty); nothing was run\n" % SECRET_ENV}
        env[payload["key_env"]] = secret
    with tempfile.TemporaryFile() as log:
        flags = {"start_new_session": True} if os.name != "nt" else {}
        try:
            p = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env, cwd=str(work), **flags)
            try:
                rc = p.wait(timeout=payload.get("timeout"))
            except subprocess.TimeoutExpired:
                _kill_group(p)
                p.wait()
                rc = -1
                log.write(("\ntimed out after %ss\n" % payload.get("timeout")).encode())
        except OSError as e:
            rc = -1
            log.write(("\ncould not start: %s\n" % e).encode())
        log.seek(0)
        text = log.read().decode("utf-8", "replace")
    if secret:
        text = text.replace(secret, "***")                 # redact first, then cut, so no fragment of the key survives
        redact_files(work, secret)
    return {"returncode": rc, "tar": pack_dir(work), "log": text[-MAX_LOG:]}


if __name__ == "__main__":
    print("remote_trial is used by modal_executor.py", file=sys.stderr)
