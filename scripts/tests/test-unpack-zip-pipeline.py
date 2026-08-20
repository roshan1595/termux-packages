#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

if os.name == "nt":
    print("unpack_zip_pipeline_skipped_windows")
    raise SystemExit(0)

repo = Path(__file__).resolve().parents[2]
script = repo / "scripts" / "build" / "get_source" / "termux_unpack_src_archive.sh"
text = script.read_text(encoding="utf-8")
assert "| head -n1" not in text, "early-closing head can deadlock unzip under PRoot"

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    cache = root / "cache"
    source = root / "source"
    cache.mkdir()
    archive = cache / "fixture.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("fixture-root/", "")
        output.writestr("fixture-root/proof.txt", "green\n")

    command = f'''set -euo pipefail
source "{script}"
TERMUX_PKG_SRCURL=("https://example.invalid/fixture.zip")
TERMUX_PKG_CACHEDIR="{cache}"
TERMUX_PKG_SRCDIR="{source}"
cd "{root}"
termux_extract_src_archive
IFS= read -r proof < "{source}/proof.txt"
test "$proof" = green
'''
    subprocess.run(["/usr/bin/bash", "-c", command], check=True, cwd=repo)

print("unpack_zip_pipeline_green")
