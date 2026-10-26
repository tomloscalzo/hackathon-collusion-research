"""Static checks on deploy/modal_vllm.py: the vLLM server key never goes on the command line.

vLLM logs its startup arguments, so ``vllm serve ... --api-key <key>`` writes the key into the Modal app logs.  The
deploy module must rely on vLLM's own ``VLLM_API_KEY`` environment variable instead (vLLM 0.8.5 and 0.9.2:
``if token := args.api_key or envs.VLLM_API_KEY`` in entrypoints/openai/api_server.py), which the container already
has from the Modal secret ``collusion-vllm-api-key``.  The module is parsed, never imported (importing it needs the
modal package and prints the deploy profile).
"""
import ast
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DEPLOY = os.path.join(HERE, "..", "..", "deploy", "modal_vllm.py")


def _source():
    with open(DEPLOY, encoding="utf-8") as f:
        return f.read()


def _strings(node):
    return [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def _is_key_flag(s):
    # anywhere in a code string (a shell-string command too); vLLM also takes --api_key
    return re.search(r"--api[-_]key(?![-\w])", s) is not None


class DeployKeyByEnvTest(unittest.TestCase):

    def setUp(self):
        self.src = _source()
        self.tree = ast.parse(self.src)
        self.docstring = ast.get_docstring(self.tree) or ""

    def _serve(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == "serve":
                return node
        self.fail("deploy/modal_vllm.py has no serve() function")

    def test_no_api_key_flag_in_any_code_string(self):
        body = [n for n in self.tree.body
                if not (isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant))]
        flags = [s for n in body for s in _strings(n) if _is_key_flag(s)]
        self.assertEqual([], flags, "vLLM logs its arguments: never pass --api-key on the vllm command line")

    def test_no_api_key_flag_in_any_vllm_command_list(self):
        found = False
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.List, ast.Tuple)):
                items = _strings(node)
                if "vllm" in items or "serve" in items or "--served-model-name" in items:
                    found = True
                    self.assertFalse([s for s in items if _is_key_flag(s)], items)
        self.assertTrue(found, "the vllm command list was not found (test out of date?)")

    def test_key_value_never_reaches_the_command(self):
        # nothing in serve() may read the key's value into the argv: only a presence check is allowed
        serve = self._serve()
        for node in ast.walk(serve):
            if isinstance(node, ast.Subscript) and "VLLM_API_KEY" in _strings(node):
                self.fail("serve() reads os.environ['VLLM_API_KEY'] (line %d): only check it is set" % node.lineno)
        for node in ast.walk(serve):
            if isinstance(node, (ast.List, ast.Tuple)) and "vllm" in _strings(node):
                self.assertNotIn("VLLM_API_KEY", _strings(node))
                for sub in ast.walk(node):
                    self.assertFalse(isinstance(sub, (ast.Subscript, ast.Call)) and "VLLM_API_KEY" in _strings(sub),
                                     "the vllm command must not carry the key (line %d)" % node.lineno)

    def test_serve_fails_closed_without_the_key(self):
        # without the env var vLLM would start an OPEN endpoint: serve() must refuse to start
        serve = self._serve()
        self.assertIn("VLLM_API_KEY", _strings(serve), "serve() must check that VLLM_API_KEY is set")
        guarded = [n for n in serve.body if isinstance(n, ast.If) and "VLLM_API_KEY" in _strings(n.test)
                   and isinstance(n.test, ast.UnaryOp) and isinstance(n.test.op, ast.Not)
                   and any(isinstance(b, ast.Raise) for b in n.body)]
        self.assertTrue(guarded, "serve() must start with `if not <VLLM_API_KEY set>: raise`")
        first_popen = min(n.lineno for n in ast.walk(serve) if isinstance(n, ast.Attribute) and n.attr == "Popen")
        self.assertLess(guarded[0].lineno, first_popen, "the key check must come before vLLM is started")

    def test_key_flag_matcher(self):
        for bad in ("--api-key", "--api-key=x", "vllm serve m --api-key $VLLM_API_KEY", "--api_key"):
            self.assertTrue(_is_key_flag(bad), bad)
        for ok in ("--api-key-env", "COLLUSION_VLLM_KEY", "--served-model-name"):
            self.assertFalse(_is_key_flag(ok), ok)

    def test_docstring_says_env_var_not_flag(self):
        self.assertNotIn("``--api-key``", self.docstring)
        self.assertNotIn("the public URL is not an open endpoint", " ".join(self.docstring.split()))
        self.assertIn("VLLM_API_KEY", self.docstring)
        self.assertIn("environment", self.docstring)

    def test_docstring_not_stale_on_apps_and_redirects(self):
        doc = " ".join(self.docstring.split())
        self.assertNotIn("but the Java client does not", doc)
        self.assertNotIn("the run would abort with HTTP 303", doc)
        self.assertIn("--follow-redirects on", doc)
        self.assertNotIn("give each deployment its own APP_NAME", doc)


if __name__ == "__main__":
    unittest.main()
