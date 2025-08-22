#!/usr/bin/env python3
"""
Flexible requirements installer.
- Attempts to install exact versions from requirements.txt
- If unavailable, tries installing without version specifier
- Skips packages that fail
"""

import subprocess
import sys
import re

def run_pip(args):
    """Run a pip command safely and return success status."""
    result = subprocess.run(
        [sys.executable, "-m", "pip"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return result.returncode == 0, result.stdout + result.stderr

def install_requirement(line: str):
    """Install a single requirement flexibly."""
    line = line.strip()
    if not line or line.startswith("#"):
        return  # ignore comments/empty lines

    # Parse package and version (supports ==, >=, <=, >, <, ~=)
    match = re.match(r"^([a-zA-Z0-9._-]+)([><=~!].+)?$", line)
    if not match:
        print(f"⚠️  Skipping unrecognized line: {line}")
        return

    package, version_spec = match.groups()
    version_spec = version_spec or ""

    full_spec = f"{package}{version_spec}"
    print(f"\n➡️  Trying to install: {full_spec}")

    # 1. Try exact spec
    success, output = run_pip(["install", full_spec])
    if success:
        print(f"✅ Installed: {full_spec}")
        return

    print(f"❌ Failed with spec {full_spec}, error: {output.strip().splitlines()[-1]}")

    # 2. Try without version spec
    print(f"➡️  Retrying without version: {package}")
    success, output = run_pip(["install", package])
    if success:
        print(f"✅ Installed: {package} (no version constraint)")
    else:
        print(f"⚠️  Skipped: {package}, installation failed")

def install_from_requirements(file_path: str):
    with open(file_path, "r") as f:
        for line in f:
            install_requirement(line)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Flexible requirements installer")
    parser.add_argument("requirements", help="Path to requirements.txt file")
    args = parser.parse_args()

    install_from_requirements(args.requirements)
