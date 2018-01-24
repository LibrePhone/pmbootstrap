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
cd "$DIR/.."

# Find CHANGEMEs in APKBUILDs
if grep -qr '(CHANGEME!)' aports/device; then
	echo "ERROR: Please replace '(CHANGEME!)' in the following files:"
	grep --color=always -r '(CHANGEME!)' aports/device
	exit 1
fi

# Shell: shellcheck
sh_files="
	./test/static_code_analysis.sh
	./test/testcases_fast.sh
	./aports/main/postmarketos-base/firmwareload.sh
	./aports/main/postmarketos-mkinitfs/init.sh.in
	./aports/main/postmarketos-mkinitfs/init_functions.sh
	./aports/main/postmarketos-mkinitfs-hook-debug-shell/20-debug-shell.sh
	./aports/main/postmarketos-update-kernel/update-kernel.sh
	./aports/main/postmarketos-android-recovery-installer/build_zip.sh
	./aports/main/postmarketos-android-recovery-installer/pmos_chroot
	./aports/main/postmarketos-android-recovery-installer/pmos_install
	./aports/main/postmarketos-android-recovery-installer/pmos_install_functions
	./aports/main/postmarketos-android-recovery-installer/pmos_setpw
	./aports/main/postmarketos-android-recovery-installer/update-binary
	./aports/main/mdss-fb-init-hack/mdss-fb-init-hack.sh
	./aports/main/postmarketos-ui-hildon/postmarketos-ui-hildon.post-install
	$(find . -path './aports/main/postmarketos-ui-hildon/*.sh')
	$(find . -name '*.trigger')
	$(find . -path './aports/main/devicepkg-dev/*.sh')
"
for file in ${sh_files}; do
	echo "Test with shellcheck: $file"
	cd "$DIR/../$(dirname "$file")"
	shellcheck -e SC1008 -x "$(basename "$file")"
done

# Python: flake8
# E501: max line length
# F401: imported, but not used, does not make sense in __init__ files
# E402: module import not on top of file, not possible for testcases
# E722: do not use bare except
cd "$DIR"/..
echo "Test with flake8: *.py"
echo "NOTE: Run 'autopep8 -ria $PWD' to fix code style issues"
py_files="$(find . -name '*.py')"
_ignores="E501,E402,E722"
# shellcheck disable=SC2086
flake8 --exclude=__init__.py --ignore "$_ignores" $py_files
# shellcheck disable=SC2086
flake8 --filename=__init__.py --ignore "F401,$_ignores" $py_files

# Done
echo "Success!"
