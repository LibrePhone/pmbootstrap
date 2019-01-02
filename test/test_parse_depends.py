"""
Copyright 2019 Oliver Smith

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

"""
This file tests all functions from pmb.parse.depends.
"""

import collections
import os
import pytest
import sys

# Import from parent directory
sys.path.insert(0, os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.config
import pmb.config.init
import pmb.helpers.logging
import pmb.parse.depends


@pytest.fixture
def args(tmpdir, request):
    import pmb.parse
    sys.argv = ["pmbootstrap", "init"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_package_from_aports(args):
    func = pmb.parse.depends.package_from_aports
    assert func(args, "invalid-package") is None
    assert func(args, "hello-world") == {"pkgname": "hello-world",
                                         "depends": [],
                                         "version": "1-r4"}


def test_package_provider(args, monkeypatch):
    # Override pmb.parse.apkindex.providers()
    providers = collections.OrderedDict()

    def return_providers(*args, **kwargs):
        return providers
    monkeypatch.setattr(pmb.parse.apkindex, "providers", return_providers)

    # Override pmb.chroot.apk.installed()
    installed = {}

    def return_installed(*args, **kwards):
        return installed
    monkeypatch.setattr(pmb.chroot.apk, "installed", return_installed)

    # 0. No provider
    pkgname = "test"
    pkgnames_install = []
    func = pmb.parse.depends.package_provider
    assert func(args, pkgname, pkgnames_install) is None

    # 1. Only one provider
    package = {"pkgname": "test", "version": "1234"}
    providers = {"test": package}
    assert func(args, pkgname, pkgnames_install) == package

    # 2. Provider with the same package name
    package_two = {"pkgname": "test-two", "provides": ["test"]}
    providers = {"test-two": package_two, "test": package}
    assert func(args, pkgname, pkgnames_install) == package

    # 3. Pick a package, that will be installed anyway
    providers = {"test_": package, "test-two": package_two}
    installed = {"test_": package}
    pkgnames_install = ["test-two"]
    assert func(args, pkgname, pkgnames_install) == package_two

    # 4. Pick a package, that is already installed
    pkgnames_install = []
    assert func(args, pkgname, pkgnames_install) == package

    # 5. Pick the first one
    installed = {}
    assert func(args, pkgname, pkgnames_install) == package


def test_package_from_index(args, monkeypatch):
    # Override pmb.parse.depends.package_provider()
    provider = None

    def return_provider(*args, **kwargs):
        return provider
    monkeypatch.setattr(pmb.parse.depends, "package_provider",
                        return_provider)

    func = pmb.parse.depends.package_from_index
    aport = {"pkgname": "test", "version": "2"}
    pkgname = "test"
    pkgnames_install = []

    # No binary package providers
    assert func(args, pkgname, pkgnames_install, aport) is aport

    # Binary package outdated
    provider = {"pkgname": "test", "version": "1"}
    assert func(args, pkgname, pkgnames_install, aport) is aport

    # Binary package up-to-date
    for version in ["2", "3"]:
        provider = {"pkgname": "test", "version": version}
        assert func(args, pkgname, pkgnames_install, aport) is provider


def test_recurse_invalid(args, monkeypatch):
    func = pmb.parse.depends.recurse

    # Invalid package
    with pytest.raises(RuntimeError) as e:
        func(args, ["invalid-pkgname"])
    assert str(e.value).startswith("Could not find dependency")


def return_none(*args, **kwargs):
    return None


def test_recurse(args, monkeypatch):
    """
    Test recursing through the following dependencies:

    test:
        libtest
        so:libtest.so.1
    libtest:
        libtest_depend
    libtest_depend:
    so:libtest.so.1:
        libtest_depend
    """
    # Override finding the package in aports: always no result
    monkeypatch.setattr(pmb.parse.depends, "package_from_aports",
                        return_none)

    # Override depends returned from APKINDEX
    depends = {
        "test": ["libtest", "so:libtest.so.1"],
        "libtest": ["libtest_depend"],
        "libtest_depend": [],
        "so:libtest.so.1": ["libtest_depend"],
    }

    def package_from_index(args, pkgname, install, aport, suffix):
        return {"pkgname": pkgname, "depends": depends[pkgname]}
    monkeypatch.setattr(pmb.parse.depends, "package_from_index",
                        package_from_index)

    # Run
    func = pmb.parse.depends.recurse
    pkgnames = ["test", "so:libtest.so.1"]
    result = ["test", "so:libtest.so.1", "libtest", "libtest_depend"]
    assert func(args, pkgnames) == result
