#!/bin/sh -e

# Disable slow testcases
# aport_in_sync_with_git: clones Alpine's aports repo
# aportgen: clones Alpine's aports repo
disabled="
	aport_in_sync_with_git
	aportgen
"

# Make sure we have a valid device (#1128)
cd "$(dirname "$0")/.."
device="$(./pmbootstrap.py config device)"
deviceinfo="$PWD/aports/device/device-$device/deviceinfo"
if ! [ -e "$deviceinfo" ]; then
	echo "ERROR: Could not find deviceinfo file for selected device '$device'."
	echo "Expected path: $deviceinfo"
	echo "Maybe you have switched to a branch where your device does not exist?"
	echo "Use 'pmbootstrap config device qemu-amd64' to switch to a valid device."
	exit 1
fi

# Filter out disabled testcases
enabled=""
for file in test/test_*.py; do
	for test in $disabled; do
		[ "test/test_${test}.py" = "$file" ] && continue 2
	done
	enabled="$enabled $file"
done

# Run enabled testcases with coverage enabled
# shellcheck disable=SC2086
pytest --cov=pmb $enabled
