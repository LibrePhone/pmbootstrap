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
import os
import sys
import pytest

# Import from parent directory
sys.path.insert(0, os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.helpers.logging
import pmb.helpers.pmaports


@pytest.fixture
def args(request, tmpdir):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)

    # Create an empty APKINDEX.tar.gz file, so we can use its path and
    # timestamp to put test information in the cache.
    apkindex_path = str(tmpdir) + "/APKINDEX.tar.gz"
    open(apkindex_path, "a").close()
    lastmod = os.path.getmtime(apkindex_path)
    args.cache["apkindex"][apkindex_path] = {"lastmod": lastmod, "multiple": {}}
    return args


def cache_apkindex(args, version):
    """
    Modify the cache of the parsed binary package repository's APKINDEX
    for the "hello-world" package.
    :param version: full version string, includes pkgver and pkgrl (e.g. 1-r2)
    """
    apkindex_path = list(args.cache["apkindex"].keys())[0]

    providers = args.cache["apkindex"][apkindex_path]["multiple"]["hello-world"]
    providers["hello-world"]["version"] = version


def test_build_is_necessary(args):
    # Prepare APKBUILD and APKINDEX data
    aport = pmb.helpers.pmaports.find(args, "hello-world")
    apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
    apkbuild["pkgver"] = "1"
    apkbuild["pkgrel"] = "2"
    indexes = list(args.cache["apkindex"].keys())
    apkindex_path = indexes[0]
    cache = {"hello-world": {"hello-world": {"pkgname": "hello-world",
                                             "version": "1-r2"}}}
    args.cache["apkindex"][apkindex_path]["multiple"] = cache

    # Binary repo has a newer version
    cache_apkindex(args, "999-r1")
    assert pmb.build.is_necessary(args, None, apkbuild, indexes) is False

    # Aports folder has a newer version
    cache_apkindex(args, "0-r0")
    assert pmb.build.is_necessary(args, None, apkbuild, indexes) is True

    # Same version
    cache_apkindex(args, "1-r2")
    assert pmb.build.is_necessary(args, None, apkbuild, indexes) is False


def test_build_is_necessary_no_binary_available(args):
    """
    APKINDEX cache is set up to fake an empty APKINDEX, which means, that the
    hello-world package has not been built yet.
    """
    indexes = list(args.cache["apkindex"].keys())
    aport = pmb.helpers.pmaports.find(args, "hello-world")
    apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
    assert pmb.build.is_necessary(args, None, apkbuild, indexes) is True
