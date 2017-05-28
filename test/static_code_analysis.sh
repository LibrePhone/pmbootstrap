#!/bin/sh
# Copyright 2017 Oliver Smith
#
# This file is part of pmbootstrap.
#
# pmbootstrap is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pmbootstrap is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pmbootstrap.  If not, see <http://www.gnu.org/licenses/>.

set -e
DIR="$(cd "$(dirname "$0")" && pwd -P)"
cd "$DIR"/..

# Shell: shellcheck
sh_files="test/static_code_analysis.sh"
echo "Test $sh_files with shellcheck..."
for file in ${sh_files}; do
	shellcheck "${file}"
done

# Python: flake8
# E501: max line length
# F401: imported, but not used, does not make sense in __init__ files
# E402: module import not on top of file, not possible for testcases
echo "Test *.py files with flake8..."
echo "NOTE: Run 'autopep8 -ria $PWD' to fix code style issues"
py_files="$(find . -name '*.py')"
_ignores="E501,E402"
# shellcheck disable=SC2086
flake8 --exclude=__init__.py --ignore "$_ignores" $py_files
# shellcheck disable=SC2086
flake8 --filename=__init__.py --ignore "F401,$_ignores" $py_files

# Done
echo "Success!"

