#!/usr/bin/env python3
"""The real CI runner must work as a Git hook, including nested test repositories.

A direct shell run lacks the Git-local environment that hooks inherit. Exercise
an actual commit with the shipped runner; stub unrelated checks, then create and
commit a child repository inside one discovered test. Before the environment
repair, that commit targets the parent's index/hook and fails recursively.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

RUNNER = Path(__file__).with_name('ci-local.sh')


class HookEnvironment(unittest.TestCase):
    def test_real_hook_can_commit_an_independent_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = {**os.environ, 'GIT_AUTHOR_NAME': 'Fixture',
                           'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
                           'GIT_COMMITTER_NAME': 'Fixture',
                           'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}
            def run(*args):
                return subprocess.run(args, cwd=root, env=environment, text=True,
                                      capture_output=True, timeout=20)
            self.assertEqual(run('git', 'init', '-q').returncode, 0)
            files = {'tools/skill-check.py': '', 'skills/primitives/visual-check.py': '',
                     'skills/forebrief/SKILL.md': '# Fixture\n',
                     'templates/claude-md/spec-driven.md': '# Fixture\n',
                     'tools/harness-inventory.sh': '#!/bin/sh\nexit 0\n',
                     'skills/probe/test-child.sh': '''#!/bin/sh
set -eu
mkdir child
cd child
git init -q
printf 'child\n' > child.txt
git add child.txt
git commit -qm child
test "$(git rev-parse --show-toplevel)" = "$PWD"
'''}
            for name, contents in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents)
                path.chmod(0o755)
            shutil.copy2(RUNNER, root / '.git/hooks/pre-commit')
            (root / '.git/hooks/pre-commit').chmod(0o755)
            self.assertEqual(run('git', 'add', 'tools', 'skills', 'templates').returncode, 0)
            result = run('git', 'commit', '-qm', 'parent')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((root / 'child/.git/HEAD').exists())


if __name__ == '__main__':
    unittest.main()
