#!/bin/sh -e
# usage: testcases_fast.sh [--all]

# Disable QEMU and aports/upstream compatibility tests
# (These run with different CI runners in parallel, see #1610)
disabled="aports aportgen upstream_compatibility soname_bump qemu_running_processes"

# Optionally enable all test cases
if [ "$1" = "--all" ]; then
    disabled=""
else
    echo "Disabled test case(s): $disabled"
    echo "Use '$(basename "$0") --all' to enable all test cases."
fi

# Make sure that the work folder format is up to date, and that there are no
# mounts from aborted test cases (#1595)
cd "$(dirname "$0")/.."
./pmbootstrap.py work_migrate
./pmbootstrap.py -q shutdown

# Make sure we have a valid device (#1128)
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
# Note: Pytest is called through python so that this is compatible with
# running from a venv (e.g. in gitlab CI)
# shellcheck disable=SC2086
python -m pytest -vv -x --cov=pmb $enabled --tb=native
