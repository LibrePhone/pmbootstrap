#!/bin/sh -e

# Go to pmbootstrap folder
DIR="$(cd "$(dirname "$0")" && pwd -P)"
cd "$DIR/.."

# Functions for pretty Travis output
. .travis/common.sh

# pmbootstrap log
fold_start "log.1" "pmbootstrap log"
cat ~/.local/var/pmbootstrap/log.txt
fold_end "log.1"

# Testsuite log
fold_start "log.2" "Testsuite log"
cat ~/.local/var/pmbootstrap/log_testsuite.txt
fold_end "log.2"
