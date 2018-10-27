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
import glob
import os
import pytest
import sys

# Import from parent directory
sys.path.insert(0, os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.build.newapkbuild
import pmb.config
import pmb.config.init
import pmb.helpers.logging


@pytest.fixture
def args(tmpdir, request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "init"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_newapkbuild(args, monkeypatch, tmpdir):
    # Fake functions
    def confirm_true(*nargs):
        return True

    def confirm_false(*nargs):
        return False

    # Preparation
    monkeypatch.setattr(pmb.helpers.cli, "confirm", confirm_false)
    pmb.build.init(args)
    args.aports = tmpdir = str(tmpdir)
    func = pmb.build.newapkbuild

    # Show the help
    func(args, "main", ["-h"])
    assert glob.glob(tmpdir + "/*") == []

    # Test package
    pkgname = "testpackage"
    func(args, "main", [pkgname])
    apkbuild_path = tmpdir + "/main/" + pkgname + "/APKBUILD"
    apkbuild = pmb.parse.apkbuild(args, apkbuild_path)
    assert apkbuild["pkgname"] == pkgname
    assert apkbuild["pkgdesc"] == ""

    # Don't overwrite
    with pytest.raises(RuntimeError) as e:
        func(args, "main", [pkgname])
    assert "Aborted" in str(e.value)

    # Overwrite
    monkeypatch.setattr(pmb.helpers.cli, "confirm", confirm_true)
    pkgdesc = "testdescription"
    func(args, "main", ["-d", pkgdesc, pkgname])
    args.cache["apkbuild"] = {}
    apkbuild = pmb.parse.apkbuild(args, apkbuild_path)
    assert apkbuild["pkgname"] == pkgname
    assert apkbuild["pkgdesc"] == pkgdesc

    # There should be no src folder
    assert not os.path.exists(tmpdir + "/main/" + pkgname + "/src")
