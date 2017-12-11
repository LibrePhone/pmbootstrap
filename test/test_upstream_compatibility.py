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
    repository = args.mirror_alpine + args.alpine_version + "/community"
    hash = pmb.helpers.repo.hash(repository)
    index_path = (args.work + "/cache_apk_armhf/APKINDEX." + hash +
                  ".tar.gz")
    index_data = pmb.parse.apkindex.read(args, "qt5-qtbase", index_path)
    pkgver_upstream = index_data["version"].split("-r")[0]

    # Iterate over our packages
    failed = []
    for path in glob.glob(args.aports + "/*/qt5-*/APKBUILD"):
        # Read the pkgver
        apkbuild = pmb.parse.apkbuild(args, path)
        pkgname = apkbuild["pkgname"]
        pkgver = apkbuild["pkgver"]

        # When we temporarily override packages from Alpine, we set the pkgver
        # to 9999 and _pkgver contains the real version (see #994).
        if pkgver == "9999":
            pkgver = apkbuild["_pkgver"]

        # Compare
        if pkgver == pkgver_upstream:
            continue
        failed.append(pkgname + ": " + pkgver + " != " +
                      pkgver_upstream)

    assert [] == failed
