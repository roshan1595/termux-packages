#!/usr/bin/env bash
set -euo pipefail

expected=${1:?expected true or false}
repo_root=$(realpath "$(dirname "${BASH_SOURCE[0]}")/../..")
source "$repo_root/scripts/build/termux_step_setup_variables.sh"

if termux_is_proot_build_environment; then
    actual=true
else
    actual=false
fi

if [[ "$actual" != "$expected" ]]; then
    echo "expected proot detection $expected, got $actual" >&2
    exit 1
fi

printf 'proot_build_detection_%s_green\n' "$expected"
