"""Batch LLM monitor on Modal: gpt-oss-120b served by vLLM INSIDE a batch function (localhost only, no public endpoint, no key).

Owner-approved for this analysis (Modal budget for the introspection-revisited workstream). New deployment, so the fastest verified
GPU class (H200, Hopper; the project's vLLM recipes are verified on Hopper). The app is its own (introspection-monitor-batch); it never
touches the game-serving apps. Containers exit when their shard is done.

    python -m modal run monitor_modal.py --inp requests.jsonl --out results.jsonl --shards 4

Created by Claude at the prompting of the repository owner.
"""
import json
import os
import subprocess
import time

import modal

MODEL = "openai/gpt-oss-120b"
REVISION = "b5c939de8f754692c1647ca79fbf85e8c1e70f8a"
GPU = "H200"
PORT = 8000

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("vllm==0.15.0", "transformers==4.56.2", "openai-harmony", "huggingface_hub[hf_transfer]", "openai>=1.40")
         .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "VLLM_NO_USAGE_STATS": "1"}))
hf_cache = modal.Volume.from_name("collusion-hf-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("collusion-vllm-cache", create_if_missing=True)
app = modal.App("introspection-monitor-batch")


@app.function(image=image, gpu=GPU, timeout=3 * 60 * 60, max_containers=6,
              volumes={"/root/.cache/huggingface": hf_cache, "/root/.cache/vllm": vllm_cache})
def run_shard(reqs: list, concurrency: int = 192) -> list:
    import asyncio
    import urllib.request

    from openai import AsyncOpenAI

    cmd = ["vllm", "serve", MODEL, "--revision", REVISION, "--tokenizer-revision", REVISION, "--host", "127.0.0.1",
           "--port", str(PORT), "--max-model-len", "32768", "--gpu-memory-utilization", "0.92", "--enable-prefix-caching",
           "--max-num-seqs", str(concurrency), "--reasoning-parser", "openai_gptoss"]
    proc = subprocess.Popen(cmd)
    t0 = time.time()
    while True:
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/health" % PORT, timeout=5)
            break
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError("vllm exited %s" % proc.returncode)
            if time.time() - t0 > 40 * 60:
                raise RuntimeError("vllm did not start")
            time.sleep(5)
    print("vllm up after %.0fs; %d requests" % (time.time() - t0, len(reqs)))
    hf_cache.commit()
    client = AsyncOpenAI(base_url="http://127.0.0.1:%d/v1" % PORT, api_key="local", timeout=900, max_retries=2)
    sem = asyncio.Semaphore(concurrency)
    done = [0]

    async def one(q):
        async with sem:
            try:
                r = await client.chat.completions.create(
                    model=MODEL, messages=q["messages"], max_tokens=q.get("max_tokens", 1500), temperature=0.0, seed=7,
                    extra_body={"chat_template_kwargs": {"reasoning_effort": q.get("effort", "low")}})
                c = r.choices[0]
                out = dict(id=q["id"], content=c.message.content, finish=c.finish_reason,
                           reasoning=(getattr(c.message, "reasoning_content", None) or "")[:3000],
                           tin=r.usage.prompt_tokens, tout=r.usage.completion_tokens)
            except Exception as ex:  # noqa: BLE001
                out = dict(id=q["id"], error=repr(ex)[:500])
            done[0] += 1
            if done[0] % 1000 == 0:
                print("done", done[0], "%.0fs" % (time.time() - t0))
            return out

    async def main():
        return await asyncio.gather(*[one(q) for q in reqs])

    res = asyncio.run(main())
    proc.terminate()
    return res


@app.local_entrypoint()
def main(inp: str, out: str, shards: int = 4, limit: int = 0, skip_done: int = 1):
    reqs = [json.loads(x) for x in open(inp, encoding="utf8")]
    have = set()
    if skip_done and os.path.exists(out):
        for x in open(out, encoding="utf8"):
            d = json.loads(x)
            if "content" in d and d.get("content"):
                have.add(d["id"])
    reqs = [q for q in reqs if q["id"] not in have]
    if limit:
        reqs = reqs[:limit]
    # long game-level requests first, interleave across shards
    reqs.sort(key=lambda q: -len(q["messages"][1]["content"]))
    parts = [reqs[i::shards] for i in range(shards)]
    parts = [p for p in parts if p]
    print("running", len(reqs), "requests in", len(parts), "shards (already have %d)" % len(have))
    with open(out, "a", encoding="utf8") as f:
        for res in run_shard.map(parts):
            for d in res:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
            f.flush()
            print("shard written", len(res))
