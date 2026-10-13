#!/usr/bin/env python3
"""Release-notice checks for update-check.py."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("update-check.py")


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid"))


class UpdateCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.remote, self.kit, self.cache = root / "remote.git", root / "kit", root / "cache"
        self.work = root / "work"
        git(root, "init", "-q", "work")
        git(self.work, "commit", "-q", "--allow-empty", "-m", "one")
        git(self.work, "tag", "v0.7.0")
        git(root, "clone", "-q", "--bare", str(self.work), str(self.remote))
        git(root, "clone", "-q", str(self.remote), str(self.kit))

    def release(self, tag):
        git(self.work, "commit", "-q", "--allow-empty", "-m", tag)
        git(self.work, "tag", tag)
        git(self.work, "push", "-q", str(self.remote), "HEAD:refs/heads/master", tag)

    def run_check(self, *args):
        result = subprocess.run(
            [sys.executable, str(CHECK), "--kit", str(self.kit), *args],
            capture_output=True, text=True, timeout=30,
            env=dict(os.environ, XDG_CACHE_HOME=str(self.cache)))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_current_kit_is_silent(self):
        self.assertEqual(self.run_check(), "")

    def test_newer_release_is_reported_with_consent_rule(self):
        self.release("v0.8.0")
        out = self.run_check()
        self.assertIn("update available: v0.8.0 (installed: v0.7.0", out)
        self.assertIn("do not update without consent", out)
        self.assertIn("pull --ff-only origin v0.8.0", out)

    def test_versions_compare_numerically(self):
        git(self.kit, "tag", "v0.10.0")
        self.release("v0.9.0")
        self.assertEqual(self.run_check(), "")

    def test_unreachable_remote_is_silent(self):
        shutil.rmtree(self.remote)
        self.assertEqual(self.run_check(), "")

    def test_cache_avoids_the_network_until_it_expires(self):
        self.release("v0.8.0")
        self.assertIn("v0.8.0", self.run_check())
        shutil.rmtree(self.remote)
        self.assertIn("v0.8.0", self.run_check())
        self.assertEqual(self.run_check("--max-age", "0"), "")

    def test_checkout_without_release_tag_is_silent(self):
        git(self.kit, "tag", "-d", "v0.7.0")
        self.release("v0.8.0")
        self.assertEqual(self.run_check(), "")


if __name__ == "__main__":
    unittest.main()
