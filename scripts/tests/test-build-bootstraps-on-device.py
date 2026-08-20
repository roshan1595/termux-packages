#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[2]
script = repo / "scripts" / "build-bootstraps.sh"
text = script.read_text(encoding="utf-8")
dependency_script = repo / "scripts" / "build" / "termux_step_get_dependencies.sh"
dependency_text = dependency_script.read_text(encoding="utf-8")
if os.name == "nt":
    print("build_bootstraps_on_device_skipped_windows")
    raise SystemExit(0)
bash = Path("/usr/bin/bash")
assert bash.is_file(), f"Bash not found at {bash}"

# Fail safely before sourcing an unmodified script, whose bottom-level main call
# would otherwise start a real bootstrap build during this test.
assert '"${BASH_SOURCE[0]}" == "$0"' in text, "bootstrap script lacks a source/direct-execution guard"
assert "TERMUX_BUILT_PACKAGES_DIRECTORY_FOR_ARCH" not in text, "undefined marker directory variable"
assert "termux_safe_clear_build_files" not in text, "force builds must not delete prior directories"
assert 'BUILD_PACKAGE_OPTIONS+=("-F")' in text, "bootstrap force mode must rebuild dependencies"
assert "TERMUX_PROPAGATE_OUTPUT_DIR_TO_DEPENDENCIES=true" in text, "bootstrap must isolate dependency debs"
assert "TERMUX_PROPAGATE_OUTPUT_DIR_TO_DEPENDENCIES" in dependency_text, "dependency builds ignore isolated output"

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

    output_dir = (fake_root / "output").as_posix()
    assert captured_args(True) == ["-o", output_dir, "zlib"]
    assert captured_args(False) == ["-a", "aarch64", "-o", output_dir, "zlib"]

    dependency_output = (fake_root / "dependency-output").as_posix()
    dependency_env = os.environ.copy()
    dependency_env["CAPTURED_ARGS"] = captured.as_posix()
    subprocess.run(
        [
            str(bash),
            "-c",
            f'''set -euo pipefail
cd "{fake_root.as_posix()}"
source "{dependency_script.as_posix()}"
termux_package__is_package_name_have_glibc_prefix() {{ return 1; }}
TERMUX_GLOBAL_LIBRARY=false
TERMUX_PACKAGE_LIBRARY=bionic
TERMUX_INSTALL_DEPS=false
TERMUX_FORCE_BUILD=true
TERMUX_FORCE_BUILD_DEPENDENCIES=true
TERMUX_PKGS__BUILD__RM_ALL_PKG_BUILD_DEPENDENT_DIRS=false
TERMUX_WITHOUT_DEPVERSION_BINDING=false
TERMUX_PACKAGE_FORMAT=debian
TERMUX_PROPAGATE_OUTPUT_DIR_TO_DEPENDENCIES=true
TERMUX_OUTPUT_DIR="{dependency_output}"
PKG=zlib
PKG_DIR=zlib
termux_run_build-package
''',
        ],
        check=True,
        cwd=repo,
        env=dependency_env,
    )
    assert captured.read_text(encoding="utf-8").splitlines() == [
        "-s",
        "-F",
        "-o",
        dependency_output,
        "--format",
        "debian",
        "--library",
        "bionic",
        "zlib",
    ]

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

    legacy_marker = fake_topdir / ".built-packages"
    legacy_output = fake_root / "output"
    legacy_marker.mkdir(parents=True)
    legacy_output.mkdir(exist_ok=True)
    marker_sentinel = legacy_marker / "must-survive"
    output_sentinel = legacy_output / "must-survive.deb"
    marker_sentinel.write_text("safe", encoding="utf-8")
    output_sentinel.write_text("safe", encoding="utf-8")
    force_env = os.environ.copy()
    force_env.update(
        {
            "TERMUX_ON_DEVICE_BUILD": "true",
            "TERMUX_PACKAGES_DIRECTORY": fake_root.as_posix(),
            "TERMUX_TOPDIR": fake_topdir.as_posix(),
        }
    )
    fresh = subprocess.check_output(
        [
            str(bash),
            "-c",
            f'''source "{script.as_posix()}"
termux_prepare_force_build_directories
printf "%s|%s" "$TERMUX_BUILT_PACKAGES_DIRECTORY" "$TERMUX_BUILT_DEBS_DIRECTORY"
''',
        ],
        cwd=repo,
        env=force_env,
        text=True,
    )
    fresh_marker_text, fresh_output_text = fresh.split("|", 1)
    fresh_marker = Path(fresh_marker_text)
    fresh_output = Path(fresh_output_text)
    assert fresh_marker.parent == fake_topdir
    assert fresh_output.parent == fake_topdir
    assert fresh_marker.is_dir() and not any(fresh_marker.iterdir())
    assert fresh_output.is_dir() and not any(fresh_output.iterdir())
    assert marker_sentinel.read_text(encoding="utf-8") == "safe"
    assert output_sentinel.read_text(encoding="utf-8") == "safe"

print("build_bootstraps_on_device_green")
