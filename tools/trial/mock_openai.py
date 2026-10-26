"""A deterministic stand-in for the OpenAI-compatible model server, for the Track M runner tests (C14.1, I3, I4). Test support only.

Standard library only; serves POST /v1/chat/completions on 127.0.0.1 (an ephemeral port) in a background thread. No network.
The reply depends only on the request (its served model name, its draw key in `user`, its last user turn), so a game
played twice, or killed and resumed from its cache, gets the same replies. The model name picks the behaviour:

  collude  talk: "Let us all hold 3.00. Agreed?" on a seat's first turn of a round, then done; quote 3.00 (the monopoly margin
           of the slice files, s0 1 and sBar 5)
  collude_declineq  as collude, but every question call is declined ("I can't help with this request.")
  compete  talk: "I will quote what suits my firm." then done; quote 1.00 (the competitive margin s0)

Any other name answers like compete. With thinking on (chat_template_kwargs.enable_thinking) the message also carries a
short reasoning_content. A question call (draw key question|...) gets a plain-text answer "mock answer of <seat> after round
<r>" (I6 canary). `delay` (seconds per call) makes a game slow enough to be killed mid-way.
Use: `with MockOpenAI(delay=0.01) as m: m.base_url`.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

QUOTES = {"collude": 3.00, "compete": 1.00, "collude_declineq": 3.00}
TALK = {"collude": "Let us all hold 3.00. Agreed?", "compete": "I will quote what suits my firm.",
        "collude_declineq": "Let us all hold 3.00. Agreed?"}


def reply_for(body):
    """(content, reasoning or None) for one chat completion request body."""
    model = body.get("model", "")
    kind = model if model in QUOTES else "compete"
    turns = [m for m in body.get("messages", []) if m.get("role") == "user"]
    last = turns[-1]["content"] if turns else ""
    user = str(body.get("user", ""))
    if user.startswith("question|"):              # I6: a plain-text answer naming the seat and round (a canary)
        parts = user.split("|")
        content = ("I held my quote; mock answer of %s after round %s." % (parts[5], parts[6][1:]) if kind != "collude_declineq"
                   else "I can't help with this request.")
    elif user.startswith("talk|"):
        first = "You have sent 0 of" in last
        content = json.dumps({"message": TALK[kind] if first else "", "done": not first})
    else:
        reply = {"quote": QUOTES[kind], "plan": "hold %.2f" % QUOTES[kind], "rationale": "mock " + kind}
        schema = ((body.get("response_format") or {}).get("json_schema") or {}).get("schema") or {}
        parts = user.split("|")
        for name, prop in (schema.get("properties") or {}).items():    # U8/U10: an extra reply field after the quote
            if name not in reply:
                reply[name] = ("I held my quote; mock in-reply answer of %s in round %s." % (parts[3], parts[4][1:]) if prop.get("type") == "string"
                               else prop.get("minimum", 1))
        content = json.dumps(reply)
    thinking = (body.get("chat_template_kwargs") or {}).get("enable_thinking")
    return content, ("mock reasoning for %s" % body.get("user", "") if thinking else None)


class MockOpenAI:
    def __init__(self, delay=0.0):
        self.delay, self.calls, self._lock = delay, 0, threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
                with outer._lock:
                    outer.calls += 1
                if outer.delay:
                    threading.Event().wait(outer.delay)
                content, reasoning = reply_for(body)
                msg = {"role": "assistant", "content": content}
                if reasoning is not None:
                    msg["reasoning_content"] = reasoning
                prompt = sum(len(m.get("content") or "") for m in body.get("messages", []))
                out = json.dumps({"id": "mock", "object": "chat.completion",
                                  "choices": [{"index": 0, "finish_reason": "stop", "message": msg}],
                                  "usage": {"prompt_tokens": (prompt + 3) // 4, "completion_tokens": (len(content) + 3) // 4}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

        class Server(ThreadingHTTPServer):
            def handle_error(self, request, client_address):    # a killed game drops its connection: not an error here
                pass

        self._server = Server(("127.0.0.1", 0), Handler)
        self.base_url = "http://127.0.0.1:%d" % self._server.server_address[1]

    def __enter__(self):
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()
        return False


if __name__ == "__main__":                      # manual use: python mock_openai.py  (serves until Ctrl-C)
    import time
    with MockOpenAI() as m:
        print(m.base_url, flush=True)
        while True:
            time.sleep(3600)
