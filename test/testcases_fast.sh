#!/bin/sh -e

# Disable slow testcases
# aport_in_sync_with_git: clones Alpine's aports repo
# aportgen: clones Alpine's aports repo
# version: clones Alpine's apk repo
disabled="
	aport_in_sync_with_git
	aportgen
	version
"

# Filter out disabled testcases
enabled=""
cd "$(dirname "$0")/.."
for file in test/test_*.py; do
	for test in $disabled; do
		[ "test/test_${test}.py" = "$file" ] && continue 2
	done
	enabled="$enabled $file"
done

# Run enabled testcases with coverage enabled
# shellcheck disable=SC2086
pytest --cov=pmb $enabled
