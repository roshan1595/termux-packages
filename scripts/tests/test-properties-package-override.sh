#!/usr/bin/env bash
set -euo pipefail

repo_root=$(realpath "$(dirname "${BASH_SOURCE[0]}")/../..")
expected="com.roshan1595.jobscout.debug"
resolved=$(
    TERMUX_APP__PACKAGE_NAME="$expected" bash -c \
        'source "$1/scripts/properties.sh"; printf "%s" "$TERMUX_APP__PACKAGE_NAME"' \
        _ "$repo_root"
)

if [[ "$resolved" != "$expected" ]]; then
    printf 'expected package override %s, got %s\n' "$expected" "$resolved" >&2
    exit 1
fi

printf 'properties_package_override_green\n'
