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

# These tests are meant to only run on the master branch
[[ $CI_COMMIT_REF_NAME != *"master"* ]] && echo "Not on master branch, so skipping tests here." && exit 0

# Init test (pipefail disabled so 'yes' doesn't fail test)
set +o pipefail
yes ''| ./pmbootstrap.py init
set -o pipefail

# test_aportgen
python -m pytest -vv --cov=pmb --tb=native ./test/test_aportgen.py

# test_soname_bump
python -m pytest -vv --cov=pmb --tb=native ./test/test_soname_bump.py

# test_upstream_compatibility
python -m pytest -vv --cov=pmb --tb=native ./test/test_upstream_compatibility.py
