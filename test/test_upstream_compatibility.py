"""
Copyright 2017 Oliver Smith

This file is part of pmbootstrap.

pmbootstrap is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pmbootstrap is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pmbootstrap.  If not, see <http://www.gnu.org/licenses/>.
"""
import os
import sys
import glob
import pytest

# Import from parent directory
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.append(pmb_src)
import pmb.parse.apkindex
import pmb.parse.apkbuild
import pmb.helpers.logging


@pytest.fixture
def args(request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_qt_versions(args):
    """
    Verify, that all postmarketOS qt5- package versions match with Alpine's
    qt5-qtbase version.
    """
    # Upstream version
    pmb.helpers.repo.update(args)
    index_data = pmb.parse.apkindex.read_any_index(args, "qt5-qtbase", "x86_64")
    pkgver_upstream = index_data["version"].split("-r")[0]

    # Check our packages
    failed = []
    for path in glob.glob(args.aports + "/*/qt5-*/APKBUILD"):
        apkbuild = pmb.parse.apkbuild(args, path)
        pkgname = apkbuild["pkgname"]
        pkgver = apkbuild["pkgver"]
        if pkgver == pkgver_upstream:
            continue
        failed.append(pkgname + ": " + pkgver + " != " +
                      pkgver_upstream)

    assert [] == failed
