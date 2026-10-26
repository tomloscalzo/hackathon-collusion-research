"""Unit G1: the gpt-oss-20b deploy profile (static: nothing is deployed, no Modal or LLM call)."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_profile_32k import DEPLOY, profiles  # noqa: E402


class GptOssProfile(unittest.TestCase):
    def test_profile_settings(self):
        p = profiles()["gpt_oss_20b"]
        self.assertEqual("collusion-vllm-gpt-oss-20b", p["app"])
        self.assertEqual("openai/gpt-oss-20b", p["model"])
        self.assertRegex(p["revision"], r"^[0-9a-f]{40}$")
        self.assertEqual(("H100", 16384, 50), (p["gpu"], p["max_model_len"], p["max_containers"]))   # cap 8 -> 50 in PR #226
        self.assertLessEqual(p["scaledown"], 300)
        self.assertEqual("openai_gptoss", p["reasoning_parser"])
        self.assertEqual("medium", p["effort"])
        self.assertIn("medium", p["variant"])

    def test_own_image_pins_and_qwen_pins_unchanged(self):
        ps = profiles()
        self.assertNotEqual(ps["qwen3_32b_fp8"]["vllm"], ps["gpt_oss_20b"]["vllm"])
        for k, v in ps.items():
            if not k.startswith("gpt_oss_20b"):   # gpt_oss_20b and its twins (_32k, _h200) have their own image
                self.assertEqual("0.9.2" if k.startswith("qwen3") else "0.8.5", v["vllm"], k)
                self.assertNotIn("transformers", v, k)
        src = DEPLOY.read_text(encoding="utf-8")
        self.assertIn('TRANSFORMERS_VERSION = "4.51.3"', src)
        self.assertIn("openai-harmony", src)

    def test_app_names_unique_and_serve_command(self):
        apps = [v["app"] for v in profiles().values()]
        self.assertEqual(len(apps), len(set(apps)))
        src = DEPLOY.read_text(encoding="utf-8")
        self.assertIn('"--default-chat-template-kwargs"', src)
        self.assertIn('"--reasoning-parser", REASONING_PARSER', src)


if __name__ == "__main__":
    unittest.main()
