"""The H200 twins of the 16k profiles (static: nothing is deployed, no Modal or LLM call)."""
import unittest

from test_profile_32k import profiles


class H200Twins(unittest.TestCase):
    def test_twins_equal_their_base_except_gpu_and_app(self):
        ps = profiles()
        for twin, base in (("qwen3_32b_fp8_h200", "qwen3_32b_fp8"), ("gpt_oss_20b_h200", "gpt_oss_20b")):
            t, b = ps[twin], ps[base]
            self.assertEqual("H200", t["gpu"])
            self.assertEqual({"gpu", "app"}, {k for k in set(t) | set(b) if t.get(k) != b.get(k)}, twin)
            self.assertEqual(b["app"] + "-h200", t["app"])
            self.assertEqual(16384, t["max_model_len"])

    def test_penalty_extension_twins_differ_only_in_app_and_gpt_oss_concurrency(self):
        ps = profiles()
        for twin, base, extra in (("qwen3_32b_fp8_h200_pe", "qwen3_32b_fp8_h200", set()),
                                  ("gpt_oss_20b_h200_pe", "gpt_oss_20b_h200", {"max_inputs"})):
            t, b = ps[twin], ps[base]
            self.assertEqual({"app"} | extra, {k for k in set(t) | set(b) if t.get(k) != b.get(k)}, twin)
            self.assertEqual(b["app"] + "-pe", t["app"])
        self.assertEqual(32, ps["gpt_oss_20b_h200_pe"]["max_inputs"])

    def test_moral_factorial_twins_differ_only_in_app_and_gpt_oss_concurrency(self):
        ps = profiles()
        for twin, base, extra in (("qwen3_32b_fp8_h200_mf", "qwen3_32b_fp8_h200", set()),
                                  ("gpt_oss_20b_h200_mf", "gpt_oss_20b_h200", {"max_inputs"})):
            t, b = ps[twin], ps[base]
            self.assertEqual({"app"} | extra, {k for k in set(t) | set(b) if t.get(k) != b.get(k)}, twin)
            self.assertEqual(b["app"] + "-mf", t["app"])
        self.assertEqual(32, ps["gpt_oss_20b_h200_mf"]["max_inputs"])


if __name__ == "__main__":
    unittest.main()
