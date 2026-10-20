#!/usr/bin/env python3
"""Cross-machine coordination checks for team-work.py: a bare remote and two clones."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(__file__).with_name("team-work.py")
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                          text=True, env=ENV).stdout.strip()


class TeamWorkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.remote = root / "remote.git"
        git(root, "init", "-q", "--bare", "-b", "main", str(self.remote))
        seed = root / "seed"
        git(root, "clone", "-q", str(self.remote), str(seed))
        (seed / "src").mkdir()
        (seed / "src" / "a.ml").write_text("let a = 1\n")
        git(seed, "add", ".")
        git(seed, "commit", "-q", "-m", "seed")
        git(seed, "push", "-q", "origin", "HEAD:main")
        self.alice, self.bob = root / "alice", root / "bob"
        for clone in (self.alice, self.bob):
            git(root, "clone", "-q", str(self.remote), str(clone))

    def run_tool(self, clone, *args, code=0, ci="success"):
        result = subprocess.run([sys.executable, str(TOOL), "--ci-status-cmd", f"echo {ci}", *args],
                                cwd=clone, capture_output=True, text=True, timeout=30, env=ENV)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def registry(self, clone):
        git(clone, "fetch", "-q", "origin", "+refs/socrask/registry:refs/socrask/r")
        return json.loads(git(clone, "show", "refs/socrask/r:registry.json"))

    def claim(self, clone, task, engineer, *paths, code=0, hours="4"):
        args = ["claim", "--task", task, "--engineer", engineer, "--criteria", "tests pass",
                "--lease-hours", hours]
        for p in paths:
            args += ["--path", p]
        return self.run_tool(clone, *args, code=code)

    def test_claims_from_two_machines_share_one_registry(self):
        self.claim(self.alice, "T-1", "alice", "src/parser")
        self.claim(self.bob, "T-2", "bob", "src/ui")
        out = self.run_tool(self.alice, "status")
        self.assertIn("T-1 [active] alice", out)
        self.assertIn("T-2 [active] bob", out)

    def test_overlap_across_machines_is_refused(self):
        self.claim(self.alice, "T-1", "alice", "src")
        out = self.claim(self.bob, "T-2", "bob", "src/a.ml", code=2)
        self.assertIn("paths overlap T-1 held by alice", out)

    def test_stale_read_is_retried_not_lost(self):
        self.claim(self.alice, "T-1", "alice", "src/x")
        # bob's last fetch predates alice's claim; his push must rebase on it.
        self.claim(self.bob, "T-2", "bob", "src/y")
        self.assertEqual(sorted(self.registry(self.alice)["tasks"]), ["T-1", "T-2"])
        log = git(self.alice, "log", "--format=%s", "refs/socrask/r")
        self.assertEqual(log.splitlines(), ["claim T-2 by bob", "claim T-1 by alice"])

    def test_simultaneous_overlapping_claims_have_one_winner(self):
        for round_ in range(3):
            procs = [subprocess.Popen(
                [sys.executable, str(TOOL), "claim", "--task", f"T-{round_}-{who}", "--engineer", who,
                 "--criteria", "tests pass", "--path", f"src/r{round_}"],
                cwd=clone, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for who, clone in (("alice", self.alice), ("bob", self.bob))]
            outputs = [p.communicate(timeout=60)[0] for p in procs]
            self.assertEqual(sorted(p.returncode for p in procs), [0, 2], outputs)
        self.assertEqual(len(self.registry(self.alice)["tasks"]), 3)

    def test_local_claim_must_stay_inside_the_team_claim(self):
        self.claim(self.alice, "T-1", "alice", "src/parser")
        local = Path(__file__).with_name("agent-work.py")
        def local_claim(path):
            return subprocess.run([sys.executable, str(local), "claim", "--task", "L-1", "--owner",
                                   "agent-a", "--role", "worker", "--coordinator", "none",
                                   "--criteria", "ok", "--path", path, "--team-task", "T-1"],
                                  cwd=self.alice, capture_output=True, text=True, env=ENV)
        out = local_claim("src/ui")
        self.assertEqual(out.returncode, 2)
        self.assertIn("outside team claim T-1", out.stderr)
        # Inside the team claim, the local rules apply as before (here: no coordinator).
        self.assertIn("worker requires an active --coordinator", local_claim("src/parser/lex.ml").stderr)

    def test_expired_lease_frees_paths_and_allows_takeover(self):
        self.claim(self.alice, "T-1", "alice", "src", hours="-1")
        self.assertIn("EXPIRED", self.run_tool(self.bob, "status"))
        self.run_tool(self.bob, "takeover", "--task", "T-1", "--engineer", "bob",
                      "--reason", "alice unreachable since yesterday")
        task = self.registry(self.bob)["tasks"]["T-1"]
        self.assertEqual(task["engineer"], "bob")
        self.assertEqual(task["history"][0]["previous"], "alice")

    def test_live_lease_cannot_be_taken_over_or_renewed_by_another(self):
        self.claim(self.alice, "T-1", "alice", "src")
        self.run_tool(self.bob, "takeover", "--task", "T-1", "--engineer", "bob",
                      "--reason", "want this work now", code=2)
        self.assertIn("belongs to alice",
                      self.run_tool(self.bob, "renew", "--task", "T-1", "--engineer", "bob", code=2))

    def test_handoff_needs_ci_success_on_the_commit(self):
        self.claim(self.alice, "T-1", "alice", "src")
        out = self.run_tool(self.alice, "handoff", "--task", "T-1", "--engineer", "alice",
                            "--pr", "https://forge/pr/1", code=2, ci="pending")
        self.assertIn("is `pending`", out)
        self.run_tool(self.alice, "handoff", "--task", "T-1", "--engineer", "alice",
                      "--pr", "https://forge/pr/1")
        self.assertEqual(self.registry(self.alice)["tasks"]["T-1"]["status"], "ready")

    def test_integrated_close_needs_the_commit_merged(self):
        self.claim(self.alice, "T-1", "alice", "src")
        (self.alice / "src" / "a.ml").write_text("let a = 2\n")
        git(self.alice, "commit", "-qam", "change")
        self.run_tool(self.alice, "handoff", "--task", "T-1", "--engineer", "alice", "--pr", "pr/1")
        close = ["close", "--task", "T-1", "--engineer", "alice", "--outcome", "integrated",
                 "--reason", "merged after review"]
        self.assertIn("not merged", self.run_tool(self.alice, *close, code=2))
        git(self.alice, "push", "-q", "origin", "HEAD:main")
        self.run_tool(self.alice, *close)
        self.assertEqual(self.registry(self.alice)["tasks"]["T-1"]["outcome"], "integrated")

    def test_kit_pin_mismatch_is_refused(self):
        (self.alice / "kb" / "work").mkdir(parents=True)
        (self.alice / "kb" / "work" / "kit-revision").write_text("0" * 40 + "\n")
        self.assertIn("differs from the project pin", self.claim(self.alice, "T-1", "alice", "src", code=2))

    def test_codeowners_outside_the_engineer_are_consulted(self):
        (self.alice / "CODEOWNERS").write_text("src/ @carol\ndocs/ @alice\n")
        out = self.claim(self.alice, "T-1", "alice", "src/a.ml", "docs")
        self.assertIn("decisions in these paths go to @carol", out)
        self.assertEqual(self.registry(self.alice)["tasks"]["T-1"]["consult"], ["@carol"])


if __name__ == "__main__":
    unittest.main()
