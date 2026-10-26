"""Run each trial as a Modal CPU function and copy its directory back (C8.3; scope section 7.1). `run_grid.py --executor modal`.

NOT RUN YET: nothing here has been executed against Modal. The Modal calls follow Modal 1.x and are marked [unsure] until the
owner approves a first live run. Tests use a fake `invoke`; they never import or call Modal.

How a trial runs: the executor sends the trial's existing files (its cache from an earlier attempt) and the command to a
Modal function (remote_trial.remote_run) in a container whose image holds JDK 17, the engine jar (/app/collusion-engine.jar)
and the scenario files (/app/scenarios). The function runs the command there and returns the whole trial directory as a
tar.gz, which is unpacked over the local trial directory; run_grid then writes DONE or FAILED as usual.
The server key never leaves Modal: the secret `collusion-vllm-api-key` (key VLLM_API_KEY) is attached to the function and
exposed to the game only as the environment variable the jar's --api-key-env names (default COLLUSION_VLLM_KEY).

Command template: as for the local executor, with the placeholders {jar}, {scenarios} and {trial_cmd} (/app/trial_cmd.py, the
Track M trial command, C14.1), and `{trial_dir}` meaning the
container's working directory. A Modal-side failure (container crash, preemption) returns nothing, so that attempt's progress is lost and the retry starts from the
files sent out; the inputs and outputs of a call are size-limited by Modal ([unsure], check on the first live run). Ctrl-C ends the app
while calls are blocked: those trials fail and are simply rerun. Each trial is one blocking call, made from one of run_grid's worker threads, so
--max-concurrency is the number of containers asked for at once (Modal's own max_containers caps it).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import remote_trial  # noqa: E402
import run_grid  # noqa: E402

REMOTE_JAR = "/app/collusion-engine.jar"
REMOTE_SCENARIOS = "/app/scenarios"
REMOTE_TRIAL_CMD = "/app/trial_cmd.py"     # the Track M trial command (C14.1), placeholder {trial_cmd}
DEFAULT_SECRET = "collusion-vllm-api-key"
DEFAULT_KEY_ENV = "COLLUSION_VLLM_KEY"


GAME_TIMEOUT = 4 * 3600                 # the game's own limit inside the container when --timeout is not given
MODAL_MARGIN = 900                      # Modal's function timeout is the game limit plus this, so the game's limit always fires first


def make_app(jar, scenarios, secret=DEFAULT_SECRET, cpu=1.0, max_containers=500, timeout=GAME_TIMEOUT + MODAL_MARGIN, memory=2048):
    """Build the Modal app and its one function; returns (app, function). Imports modal here, so nothing else needs it. [unsure]"""
    try:
        import modal
    except ImportError:
        raise RuntimeError("the modal executor needs the modal package: pip install modal (and log in); see tools/trial/modal_executor.py")
    image = (modal.Image.debian_slim(python_version="%d.%d" % sys.version_info[:2])
             .apt_install("openjdk-17-jre-headless")
             .add_local_file(str(jar), REMOTE_JAR)
             .add_local_dir(str(scenarios), REMOTE_SCENARIOS)
             .add_local_file(str(Path(__file__).resolve().parent / "trial_cmd.py"), REMOTE_TRIAL_CMD)
             .add_local_python_source("remote_trial"))
    app = modal.App("collusion-trials")

    @app.function(image=image, secrets=[modal.Secret.from_name(secret)], cpu=cpu, memory=memory, timeout=timeout,
                  max_containers=max_containers, serialized=True)
    def run_trial(payload):
        import remote_trial as rt
        return rt.remote_run(payload)

    return app, run_trial


class ModalExecutor:
    def __init__(self, template, invoke=None, key_env=DEFAULT_KEY_ENV, jar=None, scenarios=None, secret=DEFAULT_SECRET,
                 cpu=1.0, max_containers=500, memory=2048):
        self.memory = memory
        self.template, self.invoke, self.key_env = template, invoke, key_env
        self.jar, self.scenarios, self.secret, self.cpu, self.max_containers = jar, scenarios, secret, cpu, max_containers
        self._ctx = None

    def __enter__(self):
        if self.invoke is None:
            app, fn = make_app(self.jar, self.scenarios, self.secret, self.cpu, self.max_containers, memory=self.memory)
            self._ctx = app.run()
            self._ctx.__enter__()
            self.invoke = fn.remote
        return self

    def __exit__(self, *exc):
        if self._ctx is not None:
            self._ctx.__exit__(*exc)
            self._ctx = None
        return False

    def remote_argv(self, row):
        clash = [c for c in ("jar", "scenarios", "trial_cmd") if c in row]
        if clash:
            raise ValueError("grid columns %s clash with the modal placeholders" % clash)
        argv = self._argv(row)
        if "--api-key-env" not in argv or argv[argv.index("--api-key-env") + 1:][:1] != [self.key_env]:
            raise ValueError("the command must contain `--api-key-env %s` (the --key-env value), or the game gets no server key" % self.key_env)
        return argv

    def _argv(self, row):
        return run_grid.build_command(self.template, row, remote_trial.TRIAL_DIR_TOKEN,
                                      {"jar": REMOTE_JAR, "scenarios": REMOTE_SCENARIOS, "trial_cmd": REMOTE_TRIAL_CMD})

    def check(self, row):
        self.remote_argv(row)

    def run(self, row, trial_dir, timeout=None):
        d = Path(trial_dir)
        if timeout is not None and timeout > GAME_TIMEOUT:
            return run_grid.Result(-1, "--timeout %s is above the modal limit of %d s" % (timeout, GAME_TIMEOUT))
        payload = {"argv": self.remote_argv(row), "key_env": self.key_env, "timeout": timeout or GAME_TIMEOUT,
                   "files_tar": remote_trial.pack_dir(d)}
        try:
            res = self.invoke(payload)
            remote_trial.unpack(res["tar"], d)
        except Exception as e:                                  # Modal or archive trouble is a failed attempt, retried once by run_grid
            with open(d / "console.log", "a", encoding="utf-8") as f:
                f.write("--- modal attempt failed at %s: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), type(e).__name__))
            return run_grid.Result(-1, "modal call failed: %s: %s" % (type(e).__name__, e))
        with open(d / "console.log", "a", encoding="utf-8") as f:
            f.write("--- modal attempt at %s\n" % time.strftime("%Y-%m-%d %H:%M:%S") + res["log"])
        if res["returncode"] == 0:
            return run_grid.Result(0)
        return run_grid.Result(res["returncode"], "exit code %d: %s" % (res["returncode"], res["log"][-600:].strip()))
