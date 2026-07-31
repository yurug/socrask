#!/usr/bin/env python3
"""Validate the public shape and shipped document references of every skill."""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
DOC_REF = re.compile(r"`(?P<path>\.\./\.\./docs/[a-z0-9-]+\.md)`")
MARKDOWN_REF = re.compile(r"\[[^\]]+\]\((?P<path>(?!https?://|#)[^)]+\.md)\)")
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def check(skill_file: Path) -> list[str]:
    errors: list[str] = []
    text = skill_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    if len(lines) < 4 or lines[0] != "---" or "---" not in lines[1:]:
        return [f"{skill_file.relative_to(ROOT)}: missing YAML frontmatter"]

    end = lines[1:].index("---") + 1
    fields = {}
    for line in lines[1:end]:
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip("\"'")
            raw_value = value.strip()
            if ": " in raw_value and not raw_value.startswith(("\"", "'")):
                errors.append(
                    f"{skill_file.relative_to(ROOT)}: quote frontmatter values containing ': '"
                )

    unexpected = sorted(set(fields) - {"name", "description"})
    if unexpected:
        errors.append(
            f"{skill_file.relative_to(ROOT)}: unsupported frontmatter: {', '.join(unexpected)}"
        )
    name = fields.get("name", "")
    if not NAME.fullmatch(name) or name != skill_file.parent.name:
        errors.append(
            f"{skill_file.relative_to(ROOT)}: name must match its lowercase hyphenated directory"
        )
    if not fields.get("description"):
        errors.append(f"{skill_file.relative_to(ROOT)}: description is required")
    if len(lines) > 500:
        errors.append(
            f"{skill_file.relative_to(ROOT)}: {len(lines)} lines exceeds the 500-line skill budget"
        )

    references = [match.group("path") for match in DOC_REF.finditer(text)]
    references += [match.group("path") for match in MARKDOWN_REF.finditer(text)]
    for reference in sorted(set(references)):
        target = (skill_file.parent / reference).resolve()
        if not target.is_file():
            errors.append(
                f"{skill_file.relative_to(ROOT)}: missing shipped reference {reference}"
            )

    for reference in sorted(skill_file.parent.glob("references/*.md")):
        ref_lines = reference.read_text(encoding="utf-8").splitlines()
        if len(ref_lines) > 100 and "## Contents" not in ref_lines:
            errors.append(
                f"{reference.relative_to(ROOT)}: references over 100 lines need a Contents section"
            )
    return errors


def main() -> int:
    skill_files = sorted(SKILLS.glob("*/SKILL.md"))
    errors = [error for skill in skill_files for error in check(skill)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"skill-check: {len(skill_files)} skills, metadata and shipped references valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
