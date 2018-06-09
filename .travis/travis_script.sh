#!/bin/sh -e

# Go to pmbootstrap folder
DIR="$(cd "$(dirname "$0")" && pwd -P)"
cd "$DIR/.."

# Functions for pretty Travis output
. .travis/common.sh

# Wiki device documentation
fold_start "wiki_check" "Wiki device documentation"
if [ "$TRAVIS_BRANCH" = "master" ]; then
	echo "*** Pull request to master (assuming all devices boot)"
	test/check_devices_in_wiki.py --booting
else
	test/check_devices_in_wiki.py
fi
fold_end "wiki_check"

# Static code analysis
fold_start "static_analysis" "Static code analysis"
test/static_code_analysis.sh
fold_end "static_analysis"

# pmbootstrap init
fold_start "init" "pmbootstrap init"
yes "" | ./pmbootstrap.py init
fold_end "init"

# pmbootstrap kconfig_check
fold_start "kconfig_check" "pmbootstrap kconfig check"
./pmbootstrap.py kconfig check
fold_end "kconfig_check"

# pmbootstrap build --strict
fold_start "build" "pmbootstrap build --strict"
test/check_checksums.py --build
fold_end "build"

# Testsuite
fold_start "testsuite" "Testsuite and code coverage"
test/testcases_fast.sh --all
fold_end "testsuite"
