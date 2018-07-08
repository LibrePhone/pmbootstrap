#!/bin/bash
#
# This script is meant to be executed by a non-root user, since pmbootstrap
# commands will fail otherwise. This is primarily used by the gitlab CI shared
# runners.
# This script also assumes, if run outside a gitlab CI runner, that cwd is
# the root of the pmbootstrap project. For gitlab CI runners, $CI_PROJECT_DIR
# is used.
# Author: Clayton Craft <clayton@craftyguy.net>

# Return failure on any failure of commands below
set -e

# Fail quickly if run as root, since other commands here will fail
[[ "$(id -u)" != "0" ]]

# These are specific to the gitlab CI
[[ $CI_PROJECT_DIR ]] && cd "$CI_PROJECT_DIR"
# shellcheck disable=SC1091
[[ -d venv ]] && source ./venv/bin/activate

# Init test (pipefail disabled so 'yes' doesn't fail test)
set +o pipefail
yes ''| ./pmbootstrap.py init
set -o pipefail

# this seems to be needed for some tests to pass
set +o pipefail
yes | ./pmbootstrap.py zap -m -p
set -o pipefail

# testcases_fast (qemu is omitted by not passing --all)
./test/testcases_fast.sh
