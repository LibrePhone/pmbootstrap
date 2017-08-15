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
import pmb.challenge.apkindex
import pmb.config
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
    path_apkindex = str(tmpdir) + "/APKINDEX.tar.gz"
    open(path_apkindex, "a").close()
    lastmod = os.path.getmtime(path_apkindex)
    args.cache["apkindex"][path_apkindex] = {"lastmod": lastmod, "ret": {}}

    return args


def test_challenge_apkindex_extra_file(args):
    """
    Create an extra file, that is not mentioned in the APKINDEX cache.
    """
    path_apkindex = list(args.cache["apkindex"].keys())[0]
    tmpdir = os.path.dirname(path_apkindex)
    open(tmpdir + "/invalid-extra-file.apk", "a").close()

    with pytest.raises(RuntimeError) as e:
        pmb.challenge.apkindex(args, path_apkindex)
        assert "Unexpected file" in str(e.value)


def test_challenge_apkindex_file_does_not_exist(args):
    """
    Add an entry to the APKINDEX cache, that does not exist on disk.
    """
    path_apkindex = list(args.cache["apkindex"].keys())[0]
    args.cache["apkindex"][path_apkindex]["ret"] = {
        "hello-world": {"pkgname": "hello-world", "version": "1-r2"}
    }

    with pytest.raises(RuntimeError) as e:
        pmb.challenge.apkindex(args, path_apkindex)
        assert str(e.value).startswith("Could not find file 'hello-world")


def test_challenge_apkindex_ok(args):
    """
    Metion one file in the APKINDEX cache, and create it on disk. The challenge
    should go through without an exception.
    """
    path_apkindex = list(args.cache["apkindex"].keys())[0]
    args.cache["apkindex"][path_apkindex]["ret"] = {
        "hello-world": {"pkgname": "hello-world", "version": "1-r2"}
    }
    tmpdir = os.path.dirname(path_apkindex)
    open(tmpdir + "/hello-world-1-r2.apk", "a").close()

    pmb.challenge.apkindex(args, path_apkindex)
