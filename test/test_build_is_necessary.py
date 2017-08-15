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

# Import from parent directory
sys.path.append(os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.build.other
import pmb.helpers.logging


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
    setattr(args, "timestamp_based_rebuild", True)
    apkindex_path = str(tmpdir) + "/APKINDEX.tar.gz"
    open(apkindex_path, "a").close()
    lastmod = os.path.getmtime(apkindex_path)
    args.cache["apkindex"][apkindex_path] = {"lastmod": lastmod, "ret": {}}
    return args


def cache_apkindex(args, version=None, timestamp=None):
    """
    Modify the cache of the parsed binary package repository's APKINDEX
    for the "hello-world" package.

    The parameters version and timestamp are optional. If specified, they
    change the string in the cache to the new value.
    """
    apkindex_path = list(args.cache["apkindex"].keys())[0]

    if version is not None:
        args.cache["apkindex"][apkindex_path][
            "ret"]["hello-world"]["version"] = version
    if timestamp is not None:
        args.cache["apkindex"][apkindex_path][
            "ret"]["hello-world"]["timestamp"] = timestamp


def cache_files_out_of_sync(args, is_out_of_sync):
    """
    Modify the cache, so the function aports_files_out_of_sync_with_git()
    returns, that there are files out of sync for the "hello-world" package,
    or not.
    """
    new = []
    if is_out_of_sync:
        aport = pmb.build.other.find_aport(args, "hello-world")
        new = [os.path.realpath(aport + "/APKBUILD")]
    args.cache["aports_files_out_of_sync_with_git"] = new


def test_build_is_necessary(args):
    # Prepare APKBUILD and APKINDEX data
    aport = pmb.build.other.find_aport(args, "hello-world")
    apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
    apkbuild["pkgver"] = "1"
    apkbuild["pkgrel"] = "2"
    apkindex_path = list(args.cache["apkindex"].keys())[0]
    args.cache["apkindex"][apkindex_path]["ret"] = {
        "hello-world": {"pkgname": "hello-world", "version": "1-r2"}
    }

    # a) Binary repo has a newer version
    cache_apkindex(args, version="999-r1")
    assert pmb.build.is_necessary(args, None, apkbuild, apkindex_path) is False

    # b) Aports folder has a newer version
    cache_apkindex(args, version="0-r0")
    assert pmb.build.is_necessary(args, None, apkbuild, apkindex_path) is True

    # c), d) Preparation: same version
    cache_apkindex(args, version="1-r2")

    # c) Out of sync sources, newer sources
    cache_files_out_of_sync(args, True)
    cache_apkindex(args, timestamp="0")
    assert pmb.build.is_necessary(args, None, apkbuild, apkindex_path) is True

    # Timestamp based rebuild deactivated
    setattr(args, "timestamp_based_rebuild", False)
    assert pmb.build.is_necessary(args, None, apkbuild, apkindex_path) is False
    setattr(args, "timestamp_based_rebuild", True)

    # d1) Out of sync sources, old sources
    cache_files_out_of_sync(args, True)
    cache_apkindex(args, timestamp="32503680000")
    assert pmb.build.is_necessary(args, None, apkbuild, apkindex_path) is False

    # d2) Sources in sync, newer sources
    cache_files_out_of_sync(args, False)
    cache_apkindex(args, timestamp="0")
    assert pmb.build.is_necessary(args, None, apkbuild, apkindex_path) is False

    # d3) Out of sync sources, old sources
    cache_files_out_of_sync(args, False)
    cache_apkindex(args, timestamp="32503680000")
    assert pmb.build.is_necessary(args, None, apkbuild, apkindex_path) is False


def test_build_is_necessary_no_binary_available(args):
    """
    APKINDEX cache is set up to fake an empty APKINDEX, which means, that the
    hello-world package has not been built yet.
    """
    apkindex_path = list(args.cache["apkindex"].keys())[0]
    aport = pmb.build.other.find_aport(args, "hello-world")
    apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
    assert pmb.build.is_necessary(args, None, apkbuild, apkindex_path) is True
