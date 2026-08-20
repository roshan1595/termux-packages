#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[2]
script = repo / "scripts" / "build-bootstraps.sh"
text = script.read_text(encoding="utf-8")
if os.name == "nt":
    print("build_bootstraps_on_device_skipped_windows")
    raise SystemExit(0)
bash = Path("/usr/bin/bash")
assert bash.is_file(), f"Bash not found at {bash}"

# Fail safely before sourcing an unmodified script, whose bottom-level main call
# would otherwise start a real bootstrap build during this test.
assert '"${BASH_SOURCE[0]}" == "$0"' in text, "bootstrap script lacks a source/direct-execution guard"

with tempfile.TemporaryDirectory() as temporary:
    fake_root = Path(temporary)
    fake_topdir = fake_root / "topdir"
    fake_builder = fake_root / "build-package.sh"
    captured = fake_root / "captured.txt"
    fake_builder.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > \"$CAPTURED_ARGS\"\n",
        encoding="utf-8",
    )
    fake_builder.chmod(0o755)

    def captured_args(on_device: bool) -> list[str]:
        env = os.environ.copy()
        env.update(
            {
                "CAPTURED_ARGS": captured.as_posix(),
                "TERMUX_PACKAGES_DIRECTORY": fake_root.as_posix(),
                "TERMUX_TOPDIR": fake_topdir.as_posix(),
                "TERMUX_ON_DEVICE_BUILD": "true" if on_device else "false",
            }
        )
        subprocess.run(
            [
                str(bash),
                "-c",
                f'source "{script.as_posix()}"; build_package aarch64 zlib',
            ],
            check=True,
            cwd=repo,
            env=env,
        )
        return captured.read_text(encoding="utf-8").splitlines()

    assert captured_args(True) == ["zlib"]
    assert captured_args(False) == ["-a", "aarch64", "zlib"]

    autodetect_env = os.environ.copy()
    autodetect_env.pop("TERMUX_ON_DEVICE_BUILD", None)
    autodetect_env.update(
        {
            "TERMUX_PACKAGES_DIRECTORY": fake_root.as_posix(),
            "TERMUX_TOPDIR": fake_topdir.as_posix(),
        }
    )
    detected = subprocess.check_output(
        [
            str(bash),
            "-c",
            f'source "{script.as_posix()}"; printf "%s|%s" "$TERMUX_ON_DEVICE_BUILD" "$TERMUX_BUILT_PACKAGES_DIRECTORY"',
        ],
        cwd=repo,
        env=autodetect_env,
        text=True,
    )
    assert detected == f"true|{fake_topdir.as_posix()}/.built-packages"

print("build_bootstraps_on_device_green")
