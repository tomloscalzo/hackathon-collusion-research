"""Modal app that serves an open-weight instruct model through vLLM's OpenAI-compatible server (milestone M4).

*** DO NOT RUN OR DEPLOY THIS FILE UNTIL THE OWNER HAS APPROVED. ***
It was written, not executed.  Deploying it starts a billed GPU container.  Until the owner approves, every test and
every run uses the local mock server (engine/src/main/java/.../llm/MockLlmServer.java) and no paid call is made.

What it does
  * one GPU (default A10, enough for a 7-8B model in bf16), vLLM ``vllm serve`` with ``--max-model-len 4096``;
  * an API key read from the Modal secret ``collusion-vllm-api-key`` (key ``VLLM_API_KEY``) and enforced by vLLM
    from that environment variable (vLLM 0.8.5 and 0.9.2 read ``VLLM_API_KEY`` when no command-line key is given) on
    every ``/v1`` route.  vLLM does NOT check the key on its other routes (``/invocations``, which can run generation,
    ``/tokenize``, ``/health``, ...): the public URL is closed only for the OpenAI routes (open item for the owner).
    The key is never put on the vllm command line: vLLM logs its startup arguments, which would write the key into the
    Modal app logs; ``serve()`` refuses to start without a non-blank variable;
  * autoscaling to zero (``min_containers=0``, scale down after ``SCALEDOWN_SECONDS`` idle) and at most
    ``MAX_CONTAINERS`` containers (one for the default harness-check profile; up to 50 for the Qwen3 profiles, each with up
    to ``MAX_INPUTS`` concurrent requests; see PROFILES below);
  * the standard ``/v1/chat/completions`` route, which accepts per-request ``seed`` and ``temperature``; the Java client
    sends both (the seed is derived from the canonical draw key), and the request/response cache, not the server, is what
    makes runs reproducible;
  * weights are cached in a Modal volume so a cold start does not download them again.

Model identity (INTERFACES.md f.1).  The served name is derived from the weights, their pinned revision and the vLLM
version that serves them:
    SERVED_NAME = MODEL_NAME with "/" replaced by "--", "--", MODEL_REVISION, "+vllm", VLLM_VERSION[, "-", SERVED_VARIANT]
e.g. ``Qwen--Qwen2.5-7B-Instruct--<40-hex commit>+vllm0.8.5`` (``+vllm0.9.2`` for the Qwen3 profiles).  The Java client sends it as ``--model``; it becomes the
``modelSnapshot`` of every request, so it is part of every cache key, of the run lines (``llm.model``), of the manifest
(``modelSnapshot``, with ``modelId``, ``modelRevision`` and ``modelVariant`` parsed back from it) and of the analysis
grouping.  vLLM answers HTTP 404 to any other ``model`` value, so a client can only talk to these weights under this
name, and two different models, revisions or vLLM versions can never share a cache entry or an analysis group.  ``--``
and ``+`` are used instead of ``/`` and ``@`` because Hugging Face ids never contain ``--`` (so the name parses back
unambiguously) and because the experiment scripts put the model name into shard ids (directory names for ingest_merge.py) and split finding ids
on ``@``.  SERVED_VARIANT (letters, digits, ".", "_", "-") is an extra tag for any other serving change that can alter
the replies of the same weights (another dtype, for example).

Before the first deployment of a model (the module refuses to load until MODEL_REVISION is a commit hash):
  * set MODEL_NAME, MODEL_REVISION (the full 40-hex commit hash of that Hugging Face repository; a branch name such as
    "main" is refused) and GPU;
  * get the commit hash with
        python -c "from huggingface_hub import model_info; print(model_info('Qwen/Qwen2.5-7B-Instruct').sha)"
    and check the pasted value before deploying (a well-formed but wrong hash passes the check above, and vLLM would then
    fail inside a billed container until startup_timeout): this must print the same hash, a wrong one raises an error
        python -c "from huggingface_hub import model_info; print(model_info('Qwen/Qwen2.5-7B-Instruct', revision='<hash>').sha)"
  * each profile has its own app name (PROFILES below), so the Qwen3 profiles can be deployed and served at the same
    time; the URL contains the app name.

How the Java client uses it (after the owner approves; ``<workspace>`` is the Modal workspace name, ``<app>`` is APP_NAME)
    modal secret create collusion-vllm-api-key VLLM_API_KEY=<a long random string>
    modal deploy deploy/modal_vllm.py
    export COLLUSION_VLLM_KEY=<the same string>
    export COLLUSION_ALLOW_REMOTE=1          # required: the client refuses non-local hosts without it
    URL=https://<workspace>--<app>-serve.modal.run
    # Warm up first.  No container runs until a request arrives (min_containers=0) and a cold start takes minutes; Modal
    # answers a request still pending after 150 s with a 303 redirect, which curl -L follows and the Java client follows
    # with --follow-redirects on (off by default; the Track M trial command always sends it).  Each hop gets the call
    # timeout (default 120 s), so a call that may run past 150 s also needs --timeout-sec / --call-timeout-sec above 150.
    # data[0].id of the reply is the served name: pass exactly that as --model.
    SERVED=$(curl -fsSL --max-time 1200 "$URL/v1/models" -H "Authorization: Bearer $COLLUSION_VLLM_KEY" \
        | python -c "import sys, json; print(json.load(sys.stdin)['data'][0]['id'])")
    java -jar target/collusion-engine.jar run --scenario scenarios/ripe-game.yaml --seat LLM \
        --base-url "$URL" --model "$SERVED" \
        --api-key-env COLLUSION_VLLM_KEY --follow-redirects on --budget-tokens 2000000 --seed 1 --out out/runs.jsonl
The container scales to zero after SCALEDOWN_SECONDS idle; warm up again after any pause longer than that.  Check the
exact Modal and vLLM versions in the owner's account: the parameter names below follow Modal 1.x (``scaledown_window``,
``min_containers``, ``max_containers``, ``modal.concurrent``).

To stop billing: ``modal app list``, then ``modal app stop <app>`` for every app that is running (``collusion-vllm`` for
the default profile; ``collusion-vllm-qwen3-14b`` and ``collusion-vllm-qwen3-32b-fp8`` for the Qwen3 profiles, ``collusion-vllm-gpt-oss-20b`` for gpt-oss; the twins ``collusion-vllm-qwen3-32b-fp8-32k``,
``collusion-vllm-gpt-oss-20b-32k``, ``collusion-vllm-qwen3-32b-fp8-h200`` and ``collusion-vllm-gpt-oss-20b-h200``, and the moral-factorial twins ``collusion-vllm-qwen3-32b-fp8-h200-mf`` and ``collusion-vllm-gpt-oss-20b-h200-mf``; warm containers
(``COLLUSION_MIN_CONTAINERS``) bill while idle until the app is stopped), or
``modal app stop <app> --yes`` from a non-interactive shell.
"""
import json
import os
import re
import subprocess

import modal

TRANSFORMERS_VERSION = "4.51.3"           # pinned: transformers 5.x breaks vLLM 0.8.5 at start-up (no all_special_tokens_extended); verified with 0.9.2

# Deploy profiles (scope v5.4 section 7.1, interface proposal group G).  Pick one at deploy time with
#     COLLUSION_DEPLOY_PROFILE=qwen3_14b modal deploy deploy/modal_vllm.py
# The default, qwen2_5_7b, is the harness-check recipe exactly as before.  The chosen profile is baked into the image
# environment, so the container serves the same profile the deploy command chose.  COLLUSION_MAX_CONTAINERS lowers the
# container cap for a cautious run (never raises it above the profile's).
PROFILES = {
    "qwen2_5_7b": dict(app="collusion-vllm", model="Qwen/Qwen2.5-7B-Instruct",
                       revision="a09a35458c702b33eeacc393d103063234e8bc28", gpu="A10", max_model_len=4096,
                       max_inputs=32, max_containers=1, scaledown=300, reasoning=False, vllm="0.8.5"),
    "qwen3_14b": dict(app="collusion-vllm-qwen3-14b", model="Qwen/Qwen3-14B",
                      revision="40c069824f4251a91eefaf281ebe4c544efd3e18", gpu="H100", max_model_len=16384,
                      max_inputs=24, max_containers=50, scaledown=120, reasoning=True, vllm="0.9.2"),
    "qwen3_32b_fp8": dict(app="collusion-vllm-qwen3-32b-fp8", model="Qwen/Qwen3-32B-FP8",
                          revision="aa55da1ecc13d006e8b8e4f54579b1ea8c3db2df", gpu="H100", max_model_len=16384,
                          max_inputs=16, max_containers=50, scaledown=120, reasoning=True, vllm="0.9.2"),
    # Unit U11: the same pinned model and vLLM as qwen3_32b_fp8 with a 32,768-token window and fewer concurrent
    # requests (the KV cache must hold longer sequences).  Used only by the fed-back introspection arms (design
    # profile qwen3_32b_fp8_32k, context_window 32768), whose own-answer history can outgrow 16,384.
    # GPU H200 (owner, 2026-10-25: "Use the faster GPU's for any new work"): the same Hopper architecture and FP8 kernels as H100,
    # with more memory and bandwidth; B200 (Blackwell) is not chosen because this pinned vLLM 0.9.2 recipe was only verified on Hopper.
    # Model, revision, vLLM and served name are unchanged (the GPU is not part of the served name).
    "qwen3_32b_fp8_32k": dict(app="collusion-vllm-qwen3-32b-fp8-32k", model="Qwen/Qwen3-32B-FP8",
                              revision="aa55da1ecc13d006e8b8e4f54579b1ea8c3db2df", gpu="H200", max_model_len=32768,
                              max_inputs=8, max_containers=50, scaledown=120, reasoning=True, vllm="0.9.2"),
    # Unit G1: gpt-oss-20b (harmony format, MXFP4 weights, always-on reasoning).  Its OWN image: vLLM 0.15.0 (torch 2.9.1; 0.11.0 lacks
    # --default-chat-template-kwargs, first present in 0.15.0 (live check); openai_gptoss parser present), transformers
    # 4.56.2 and openai-harmony; the Qwen pins above are untouched.  Reasoning effort cannot be switched off: it is fixed to
    # "medium" on the SERVER (--default-chat-template-kwargs, merged under the client's chat_template_kwargs.enable_thinking,
    # which gpt-oss ignores) and recorded in the served name through the variant tag.
    "gpt_oss_20b": dict(app="collusion-vllm-gpt-oss-20b", model="openai/gpt-oss-20b",
                        revision="6cee5e81ee83917806bbde320786a8fb61efebee", gpu="H100", max_model_len=16384,
                        max_inputs=16, max_containers=50, scaledown=300, reasoning=True, vllm="0.15.0",
                        transformers="4.56.2", reasoning_parser="openai_gptoss", effort="medium",
                        variant="effort-medium"),
    # The 32k-window twin of gpt_oss_20b (same model, revision, vLLM, effort and variant tag, so the same served name; only max_model_len
    # 32768 and its own app and URL), for the fed-back introspection arms r2f / r3f whose own-answer history can outgrow 16,384.
    "gpt_oss_20b_32k": dict(app="collusion-vllm-gpt-oss-20b-32k", model="openai/gpt-oss-20b",
                            revision="6cee5e81ee83917806bbde320786a8fb61efebee", gpu="H100", max_model_len=32768,
                            max_inputs=16, max_containers=8, scaledown=300, reasoning=True, vllm="0.15.0",
                            transformers="4.56.2", reasoning_parser="openai_gptoss", effort="medium",
                            variant="effort-medium"),
    # H200 twins of the 16k profiles, each with its OWN app and URL (owner, 2026-10-25: "Use the faster GPU's for any new work"), so a new
    # run gets fresh, warm containers without redeploying an app another run may be using.  Model, revision, vLLM, window, sampling-side
    # settings and served name are identical to the H100 profile (the GPU is not part of the served name); only gpu and app differ.
    # H200 (Hopper, as H100, with more memory and bandwidth), not B200: the pinned recipes were only verified on Hopper (as PR #248).
    "qwen3_32b_fp8_h200": dict(app="collusion-vllm-qwen3-32b-fp8-h200", model="Qwen/Qwen3-32B-FP8",
                               revision="aa55da1ecc13d006e8b8e4f54579b1ea8c3db2df", gpu="H200", max_model_len=16384,
                               max_inputs=16, max_containers=50, scaledown=120, reasoning=True, vllm="0.9.2"),
    "gpt_oss_20b_h200": dict(app="collusion-vllm-gpt-oss-20b-h200", model="openai/gpt-oss-20b",
                             revision="6cee5e81ee83917806bbde320786a8fb61efebee", gpu="H200", max_model_len=16384,
                             max_inputs=16, max_containers=50, scaledown=300, reasoning=True, vllm="0.15.0",
                             transformers="4.56.2", reasoning_parser="openai_gptoss", effort="medium",
                             variant="effort-medium"),
    # Penalty-extension twins (owner, 2026-10-26: new apps on the fastest GPU class with warm containers, so this run never shares an app
    # with another agent's run).  Each equals its *_h200 profile except app; the gpt-oss twin also allows 32 concurrent requests per
    # container (vLLM --max-num-seqs 32; gpt-oss-20b's KV cache is small) to fit 300 games under the $60 cap.  Model, revision, vLLM,
    # window, effort and served name are unchanged, so trial ids, cache identity and the model snapshot match the earlier runs.
    "qwen3_32b_fp8_h200_pe": dict(app="collusion-vllm-qwen3-32b-fp8-h200-pe", model="Qwen/Qwen3-32B-FP8",
                                  revision="aa55da1ecc13d006e8b8e4f54579b1ea8c3db2df", gpu="H200", max_model_len=16384,
                                  max_inputs=16, max_containers=50, scaledown=120, reasoning=True, vllm="0.9.2"),
    "gpt_oss_20b_h200_pe": dict(app="collusion-vllm-gpt-oss-20b-h200-pe", model="openai/gpt-oss-20b",
                                revision="6cee5e81ee83917806bbde320786a8fb61efebee", gpu="H200", max_model_len=16384,
                                max_inputs=32, max_containers=50, scaledown=300, reasoning=True, vllm="0.15.0",
                                transformers="4.56.2", reasoning_parser="openai_gptoss", effort="medium",
                                variant="effort-medium"),
    # Moral-factorial twins (owner, 2026-10-26: new H200 apps with warm containers, so this run never shares an app with another agent's
    # run).  Each equals its *_h200 profile except app; the gpt-oss twin also allows 32 concurrent requests per container (vLLM
    # --max-num-seqs 32; gpt-oss-20b's KV cache is small) to fit the run under the $60 cap.  Model, revision, vLLM, window, effort and
    # served name are unchanged, so trial ids, cache identity and the model snapshot match the earlier moral-prime runs.
    "qwen3_32b_fp8_h200_mf": dict(app="collusion-vllm-qwen3-32b-fp8-h200-mf", model="Qwen/Qwen3-32B-FP8",
                                  revision="aa55da1ecc13d006e8b8e4f54579b1ea8c3db2df", gpu="H200", max_model_len=16384,
                                  max_inputs=16, max_containers=50, scaledown=120, reasoning=True, vllm="0.9.2"),
    "gpt_oss_20b_h200_mf": dict(app="collusion-vllm-gpt-oss-20b-h200-mf", model="openai/gpt-oss-20b",
                                revision="6cee5e81ee83917806bbde320786a8fb61efebee", gpu="H200", max_model_len=16384,
                                max_inputs=32, max_containers=50, scaledown=300, reasoning=True, vllm="0.15.0",
                                transformers="4.56.2", reasoning_parser="openai_gptoss", effort="medium",
                                variant="effort-medium"),
}
PROFILE_NAME = os.environ.get("COLLUSION_DEPLOY_PROFILE", "qwen2_5_7b")
if PROFILE_NAME not in PROFILES:
    raise ValueError("COLLUSION_DEPLOY_PROFILE %r is not one of %s" % (PROFILE_NAME, sorted(PROFILES)))
PROFILE = PROFILES[PROFILE_NAME]

APP_NAME = PROFILE["app"]
MODEL_NAME = PROFILE["model"]
MODEL_REVISION = PROFILE["revision"]      # the 40-hex commit hash of MODEL_NAME (see above)
SERVED_VARIANT = PROFILE.get("variant", "")   # optional extra serving tag; empty for the Qwen profiles, effort-medium for gpt-oss
GPU = PROFILE["gpu"]
MAX_MODEL_LEN = PROFILE["max_model_len"]
MAX_INPUTS = PROFILE["max_inputs"]        # concurrent requests per container; vLLM's --max-num-seqs matches it
_cap = int(os.environ.get("COLLUSION_MAX_CONTAINERS", PROFILE["max_containers"]))
if _cap < 1:
    raise ValueError("COLLUSION_MAX_CONTAINERS must be at least 1, got %d" % _cap)
MAX_CONTAINERS = min(PROFILE["max_containers"], _cap)
# COLLUSION_MIN_CONTAINERS keeps that many containers warm (owner, 2026-10-25: "keep containers warm"); default 0 (scale to zero,
# as before); never above MAX_CONTAINERS.  Warm containers bill while idle: stop the app when its run is done.
MIN_CONTAINERS = int(os.environ.get("COLLUSION_MIN_CONTAINERS", "0"))
if not 0 <= MIN_CONTAINERS <= MAX_CONTAINERS:
    raise ValueError("COLLUSION_MIN_CONTAINERS must be between 0 and %d, got %d" % (MAX_CONTAINERS, MIN_CONTAINERS))
print("deploy profile %s: app %s, %s on %s, max_containers %d, min_containers %d" % (PROFILE_NAME, PROFILE["app"], PROFILE["model"],
                                                                                     PROFILE["gpu"], MAX_CONTAINERS, MIN_CONTAINERS))
VLLM_VERSION = PROFILE["vllm"]            # part of the served name: a version bump is a new model identity.  The Qwen3
                                          # profiles need 0.9.x: vLLM 0.8.5 has no qwen3 reasoning parser (live check)
REASONING = PROFILE["reasoning"]          # Qwen3: serve with the qwen3 reasoning parser; thinking is a request field
REASONING_PARSER = PROFILE.get("reasoning_parser", "qwen3")
REASONING_EFFORT = PROFILE.get("effort", "")   # gpt-oss only: the server-side default reasoning effort
IMAGE_TRANSFORMERS = PROFILE.get("transformers", TRANSFORMERS_VERSION)
PORT = 8000
SCALEDOWN_SECONDS = PROFILE["scaledown"]  # idle seconds before the container scales to zero

_ID_PART = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"   # same rule as llm.ModelIdentity
_HF_ID = re.compile(_ID_PART + "(?:/" + _ID_PART + ")?")
_COMMIT = re.compile(r"[0-9a-f]{40}")
_TAG = re.compile(r"[A-Za-z0-9._-]+")


def served_name(model_name, revision, vllm_version, extra=""):
    """The served model name for these weights at this revision under this vLLM version (the --model value of the client)."""
    if not _HF_ID.fullmatch(model_name) or "--" in model_name or ".." in model_name:
        raise ValueError("MODEL_NAME %r is not a Hugging Face model id (org/name)" % model_name)
    if not _COMMIT.fullmatch(revision):
        raise ValueError("MODEL_REVISION %r must be the full 40-hex commit hash of %s, not a branch or tag; get it with "
                         "python -c \"from huggingface_hub import model_info; print(model_info('%s').sha)\""
                         % (revision, model_name, model_name))
    if not _TAG.fullmatch(vllm_version) or (extra and not _TAG.fullmatch(extra)):
        raise ValueError("VLLM_VERSION %r and SERVED_VARIANT %r may contain only letters, digits, '.', '_' and '-'"
                         % (vllm_version, extra))
    return model_name.replace("/", "--") + "--" + revision + "+vllm" + vllm_version + ("-" + extra if extra else "")


SERVED_NAME = served_name(MODEL_NAME, MODEL_REVISION, VLLM_VERSION, SERVED_VARIANT)   # refuses an unpinned recipe

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(f"vllm=={VLLM_VERSION}", f"transformers=={IMAGE_TRANSFORMERS}", "huggingface_hub[hf_transfer]",
                 *(["openai-harmony"] if PROFILE_NAME.startswith("gpt_oss_20b") else []))
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "VLLM_NO_USAGE_STATS": "1",
          "COLLUSION_DEPLOY_PROFILE": PROFILE_NAME, "COLLUSION_MAX_CONTAINERS": str(MAX_CONTAINERS),
          "COLLUSION_MIN_CONTAINERS": str(MIN_CONTAINERS)})
)

hf_cache = modal.Volume.from_name("collusion-hf-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("collusion-vllm-cache", create_if_missing=True)

app = modal.App(APP_NAME)


@app.function(
    image=image,
    gpu=GPU,
    scaledown_window=SCALEDOWN_SECONDS,
    min_containers=MIN_CONTAINERS,
    max_containers=MAX_CONTAINERS,
    timeout=60 * 60,
    volumes={"/root/.cache/huggingface": hf_cache, "/root/.cache/vllm": vllm_cache},
    secrets=[modal.Secret.from_name("collusion-vllm-api-key")],
)
@modal.concurrent(max_inputs=MAX_INPUTS)
@modal.web_server(port=PORT, startup_timeout=15 * 60)
def serve():
    """Start vLLM's OpenAI-compatible server inside the container (exposed on ``PORT``).

    The key reaches vLLM only through the inherited environment variable VLLM_API_KEY (from the Modal secret): vLLM logs
    its command-line arguments, so the key must never be one of them.  Without the variable vLLM would serve the /v1
    routes without authentication, so the container refuses to start.
    """
    if not os.environ.get("VLLM_API_KEY", "").strip():
        raise RuntimeError("VLLM_API_KEY is not set: the Modal secret collusion-vllm-api-key must hold it "
                           "(vLLM would otherwise serve without authentication)")
    cmd = [
        "vllm", "serve", MODEL_NAME,
        "--revision", MODEL_REVISION,
        "--tokenizer-revision", MODEL_REVISION,   # the tokenizer and chat template come from the same pinned commit
        "--served-model-name", SERVED_NAME,
        "--host", "0.0.0.0",
        "--port", str(PORT),
        "--max-model-len", str(MAX_MODEL_LEN),
        "--dtype", "auto",
        "--gpu-memory-utilization", "0.90",
        "--enable-prefix-caching",
    ]
    if PROFILE_NAME != "qwen2_5_7b":
        cmd += ["--max-num-seqs", str(MAX_INPUTS)]
    if REASONING:
        cmd += ["--reasoning-parser", REASONING_PARSER]   # in vLLM 0.9.x the parser alone enables reasoning output
    if REASONING_EFFORT:
        cmd += ["--default-chat-template-kwargs", json.dumps({"reasoning_effort": REASONING_EFFORT})]
    subprocess.Popen(cmd)  # inherits os.environ (VLLM_API_KEY); the web_server decorator waits for the port to open
