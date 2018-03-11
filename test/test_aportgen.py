"""
Copyright 2018 Oliver Smith

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
sys.path.append(os.path.realpath(
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
    return args


def test_aportgen(args, tmpdir):
    # Fake aports folder in tmpdir
    aports_real = args.aports
    args.aports = str(tmpdir)
    pmb.helpers.run.user(args, ["mkdir", "-p", str(tmpdir) + "/cross"])

    # Create aportgen folder -> code path where it still exists
    pmb.helpers.run.user(args, ["mkdir", "-p", args.work + "/aportgen"])

    # Generate all valid packages (gcc twice -> different code path)
    pkgnames = ["binutils-armhf", "musl-armhf", "busybox-static-armhf",
                "gcc-armhf", "gcc-armhf"]
    for pkgname in pkgnames:
        pmb.aportgen.generate(args, pkgname)
        path_new = args.aports + "/cross/" + pkgname + "/APKBUILD"
        path_old = aports_real + "/cross/" + pkgname + "/APKBUILD"
        assert os.path.exists(path_new)
        assert filecmp.cmp(path_new, path_old, False)


def test_aportgen_invalid_generator(args):
    with pytest.raises(ValueError) as e:
        pmb.aportgen.generate(args, "pkgname-with-no-generator")
    assert "No generator available" in str(e.value)


def test_aportgen_get_upstream_aport(args, monkeypatch):

    # Fake pmb.parse.apkbuild()
    def fake_apkbuild(*args, **kwargs):
        return apkbuild
    monkeypatch.setattr(pmb.parse, "apkbuild", fake_apkbuild)

    # Fake pmb.parse.apkindex.package()
    def fake_package(*args, **kwargs):
        return package
    monkeypatch.setattr(pmb.parse.apkindex, "package", fake_package)

    # Equal version
    func = pmb.aportgen.core.get_upstream_aport
    upstream = "main/gcc"
    upstream_full = args.work + "/cache_git/aports_upstream/" + upstream
    apkbuild = {"pkgver": "2.0", "pkgrel": "0"}
    package = {"version": "2.0-r0"}
    assert func(args, upstream) == upstream_full

    # APKBUILD < binary
    apkbuild = {"pkgver": "1.0", "pkgrel": "0"}
    package = {"version": "2.0-r0"}
    with pytest.raises(RuntimeError) as e:
        func(args, upstream)
    assert str(e.value).startswith("You can update your local checkout with")

    # APKBUILD > binary
    apkbuild = {"pkgver": "3.0", "pkgrel": "0"}
    package = {"version": "2.0-r0"}
    with pytest.raises(RuntimeError) as e:
        func(args, upstream)
    assert str(e.value).startswith("You can force an update of your binary")
