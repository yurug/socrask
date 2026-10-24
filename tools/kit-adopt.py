#!/usr/bin/env python3
"""kit-adopt — vendor kit files with provenance, and adopt features by level.

Projects copy kit tools into their own `tools/`. Without a contract, each
project invents its own manifest, local copies drift, and every release reads
as "adopt everything". This tool gives the copy a contract and the adoption a
pace.

Usage (from the project root; vendor/status/upgrade run the kit checkout's copy):
    kit-adopt.py vendor SOURCE... [--dest tools]   copy kit files byte for byte
    kit-adopt.py upgrade [--to TAG]                re-vendor every file from TAG
    kit-adopt.py status                            what changed upstream since the pin
    kit-adopt.py check                             integrity and adoption (CI)
    kit-adopt.py features                          the feature catalogue

Files in the project:
    tools/socrask.json      manifest: repository, revision, tag, and per vendored
                            file {"source": kit path, "sha256": ...}
    kb/work/adoption.json   {"kit_tag": TAG, "features": {id: {"state":
                            "adopted|not-applicable|deferred", "reason", "task",
                            "review_on": "YYYY-MM-DD"}}}

Levels (tools/kit-features.json): an essential feature is adopted, or deferred
with a task and a review date. A triggered feature is adopted when its trigger
holds, and otherwise recorded as not-applicable with the reason. An optional
feature needs no record.

check (E = error, W = warning):
    E-integrity   a vendored file differs from its manifest hash: local edits
                  belong upstream, notes belong in the KB
    E-legacy      tools/agentic-dev-kit.json, the manifest from before the rename
    E-version     adoption.json's kit_tag differs from the manifest tag
    E-adoption    an essential feature recorded not-applicable; a deferred one
                  without task or review_on; a not-applicable one without
                  reason; an adopted one whose tools are not vendored; an
                  unknown feature
    W-revisit     a deferred feature past its review_on date
    W-unrecorded  an essential or triggered feature with no record yet

What this does NOT do: judge whether a trigger holds, or merge local changes
into an upstream release.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys

KIT = Path(__file__).resolve().parent.parent
MANIFEST, ADOPTION = Path("tools/socrask.json"), Path("kb/work/adoption.json")
LEGACY = Path("tools/agentic-dev-kit.json")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def kit_git(*args):
    out = subprocess.run(["git", "-C", str(KIT), *args], capture_output=True)
    if out.returncode:
        raise ValueError(f"kit checkout: git {' '.join(args)}: {out.stderr.decode().strip()}")
    return out.stdout


def kit_source(name):
    """Resolve a bare tool name or a kit path to the kit path that holds it."""
    for candidate in (name, f"tools/{name}", f"skills/spec-driven-dev/{name}"):
        if (KIT / candidate).is_file():
            return candidate
    raise ValueError(f"{name}: not a file of the kit at {KIT}")


def catalogue():
    for place in (KIT / "tools/kit-features.json", Path("tools/kit-features.json")):
        if place.is_file():
            return json.loads(place.read_text())["features"]
    raise ValueError("tools/kit-features.json not found (vendor it with this tool)")


def load_manifest():
    return json.loads(MANIFEST.read_text()) if MANIFEST.is_file() else {"files": {}}


def save_manifest(m):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")


def pin(m, rev):
    m["repository"] = "https://github.com/yurug/socrask"
    m["revision"] = kit_git("rev-parse", rev).decode().strip()
    m["tag"] = kit_git("describe", "--tags", "--always", rev).decode().strip()


def tags():
    out = kit_git("tag", "--list", "v*", "--sort=-v:refname").decode().split()
    return out


def vendor(args):
    if kit_git("status", "--porcelain").strip():
        raise ValueError("the kit checkout has local changes; vendor from a clean release")
    m = load_manifest()
    pin(m, "HEAD")
    for name in args.sources:
        src = kit_source(name)
        dest = Path(args.dest) / Path(src).name
        data = (KIT / src).read_bytes()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        dest.chmod((KIT / src).stat().st_mode)
        m["files"][str(dest)] = {"source": src, "sha256": sha(data)}
        print(f"vendored {src} -> {dest}")
    save_manifest(m)
    print(f"pinned {m['tag']} ({m['revision'][:12]}) in {MANIFEST}")
    return 0


def upgrade(args):
    m = load_manifest()
    target = args.to or tags()[0]
    for dest, entry in m["files"].items():
        if not isinstance(entry, dict):
            raise ValueError(f"{dest}: legacy manifest entry without source; re-vendor it")
        data = kit_git("show", f"{target}:{entry['source']}")
        Path(dest).write_bytes(data)
        entry["sha256"] = sha(data)
    pin(m, target)
    save_manifest(m)
    print(f"upgraded {len(m['files'])} files to {m['tag']}; update kb/work/adoption.json kit_tag "
          "and record the new features (`kit-adopt.py status`)")
    return 0


def status(_args):
    m, latest = load_manifest(), tags()[0]
    pinned = m.get("revision")
    print(f"pinned {m.get('tag', 'nothing')}; latest release {latest}")
    if not pinned:
        return 0
    for dest, entry in sorted(m["files"].items()):
        src = entry["source"] if isinstance(entry, dict) else None
        if src and kit_git("diff", "--name-only", pinned, latest, "--", src).strip():
            print(f"  changed upstream: {dest} ({src})")
    pinned_tag = m.get("tag", "v0.0.0").split("-")[0]
    key = lambda t: tuple(int(x) for x in t.lstrip("v").split("."))
    for fid, f in sorted(catalogue().items()):
        if key(f["since"]) > key(pinned_tag):
            what = f.get("trigger") or f.get("summary")
            print(f"  new {f['level']} feature {fid} ({f['since']}): {what}")
    return 0


def check(_args):
    errors, warnings = [], []
    if LEGACY.is_file():
        errors.append(f"E-legacy: {LEGACY} predates the rename to Socrask; re-vendor its files with "
                      "kit-adopt.py vendor and delete it")
    m = load_manifest()
    for dest, entry in sorted(m.get("files", {}).items()):
        want = entry["sha256"] if isinstance(entry, dict) else entry
        path = Path(dest)
        if not path.is_file():
            errors.append(f"E-integrity: {dest} is in the manifest but missing")
        elif sha(path.read_bytes()) != want:
            errors.append(f"E-integrity: {dest} differs from {m.get('tag')}; move local changes "
                          "upstream or into the KB, then re-vendor")
    if ADOPTION.is_file():
        adoption = json.loads(ADOPTION.read_text())
        features = catalogue()
        if m.get("tag") and adoption.get("kit_tag") != m["tag"]:
            errors.append(f"E-version: {ADOPTION} records {adoption.get('kit_tag')} but the manifest "
                          f"pins {m['tag']}")
        vendored = {Path(d).name for d in m.get("files", {})}
        records = adoption.get("features", {})
        for fid, rec in records.items():
            if fid not in features:
                errors.append(f"E-adoption: unknown feature {fid}")
                continue
            level, state = features[fid]["level"], rec.get("state")
            if state == "adopted":
                missing = [t for t in features[fid]["tools"] if t not in vendored and not Path("tools", t).is_file()]
                if missing:
                    errors.append(f"E-adoption: {fid} adopted but {', '.join(missing)} not vendored")
            elif state == "not-applicable":
                if level == "essential":
                    errors.append(f"E-adoption: {fid} is essential; adopt it or defer it with a task")
                elif not rec.get("reason"):
                    errors.append(f"E-adoption: {fid} not-applicable needs the reason the trigger does not hold")
            elif state == "deferred":
                if not rec.get("task") or not rec.get("review_on"):
                    errors.append(f"E-adoption: {fid} deferred needs task and review_on")
                elif date.fromisoformat(rec["review_on"]) < date.today():
                    warnings.append(f"W-revisit: {fid} was deferred until {rec['review_on']}; adopt it "
                                    "or record a new decision")
            else:
                errors.append(f"E-adoption: {fid} has state `{state}`")
        for fid, f in sorted(features.items()):
            if f["level"] != "optional" and fid not in records:
                warnings.append(f"W-unrecorded: {f['level']} feature {fid} has no adoption record")
    for line in errors + warnings:
        print(line)
    print(f"kit-adopt: {len(m.get('files', {}))} vendored files, {len(errors)} errors, "
          f"{len(warnings)} warnings")
    return 1 if errors else 0


def features(_args):
    for fid, f in sorted(catalogue().items(), key=lambda kv: (kv[1]["level"], kv[0])):
        print(f"{f['level']:<9} {fid:<20} {f['since']:<8} {f.get('trigger') or f.get('summary')}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="action", required=True)
    v = sub.add_parser("vendor")
    v.add_argument("sources", nargs="+")
    v.add_argument("--dest", default="tools")
    u = sub.add_parser("upgrade")
    u.add_argument("--to")
    for name in ("status", "check", "features"):
        sub.add_parser(name)
    args = ap.parse_args()
    return {"vendor": vendor, "upgrade": upgrade, "status": status, "check": check,
            "features": features}[args.action](args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        print(f"kit-adopt: {exc}", file=sys.stderr)
        sys.exit(2)
