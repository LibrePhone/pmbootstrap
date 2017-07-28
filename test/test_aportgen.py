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
import pytest
import filecmp

# Import from parent directory
sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.aportgen
import pmb.config
import pmb.helpers.logging


@pytest.fixture
def args(tmpdir, request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    setattr(args, "_aports_real", args.aports)
    args.aports = str(tmpdir)
    pmb.helpers.run.user(args, ["mkdir", "-p", str(tmpdir) + "/cross"])
    return args


def test_aportgen(args):
    # Create aportgen folder -> code path where it still exists
    pmb.helpers.run.user(args, ["mkdir", "-p", args.work + "/aportgen"])

    # Generate all valid packages
    pkgnames = []
    for arch in pmb.config.build_device_architectures:
        # gcc twice, so the output folder already exists -> different code path
        for pkgname in ["binutils", "musl", "busybox-static", "gcc", "gcc"]:
            pkgnames.append(pkgname + "-" + arch)
    for pkgname in pkgnames:
        pmb.aportgen.generate(args, pkgname)
        path_new = args.aports + "/cross/" + pkgname + "/APKBUILD"
        path_old = args._aports_real + "/cross/" + pkgname + "/APKBUILD"
        assert os.path.exists(path_new)
        assert filecmp.cmp(path_new, path_old, False)


def test_aportgen_invalid_generator(args):
    with pytest.raises(ValueError) as e:
        pmb.aportgen.generate(args, "pkgname-with-no-generator")
    assert "No generator available" in str(e.value)
