#!/usr/bin/env python3
"""Secret-in-log checks for log-check.py."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("log-check.py")


class LogCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_check(self, files, *args, code=0):
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        result = subprocess.run([sys.executable, str(CHECK), str(self.root), *args],
                                capture_output=True, text=True, timeout=10)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def test_secret_in_log_calls_fails_across_languages(self):
        out = self.run_check({
            "a.py": 'logger.info("login %s", password)\n',
            "b.ts": "console.log(`key=${apiKey}`)\n",
            "c.rs": 'info!("auth {}", access_token);\n',
            "d.ml": 'Logs.info (fun m -> m "secret %s" client_secret)\n',
        }, code=1)
        self.assertEqual(out.count("E-secret-log"), 4)
        self.assertIn("a.py:1: E-secret-log: log call names `password`", out)

    def test_plain_tokens_and_non_log_lines_pass(self):
        self.run_check({
            "lexer.ml": 'Logs.debug (fun m -> m "next token %a" pp tok)\n',
            "auth.py": "password = read_password()\nlogger.info('login ok', user_id)\n",
        })

    def test_suppression_needs_a_reason(self):
        self.run_check({"a.py": "# log-check: ok logs the field name only\n"
                                "logger.info('missing field: password')\n"})
        self.run_check({"a.py": "logger.info('password')  # log-check: ok\n"}, code=1)

    def test_exclude_glob_skips_files(self):
        self.run_check({"test-x.py": "logger.info(password)\n"}, "--exclude", "test-*")

    def test_vendor_and_build_directories_are_skipped(self):
        self.run_check({"node_modules/x/a.js": "console.log(password)\n",
                        "_build/a.ml": 'Logs.info (fun m -> m "%s" password)\n'})


if __name__ == "__main__":
    unittest.main()
