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
import pytest
import sys

# Import from parent directory
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, pmb_src)
import pmb.helpers.repo


@pytest.fixture
def args(tmpdir, request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_hash():
    url = "https://nl.alpinelinux.org/alpine/edge/testing"
    hash = "865a153c"
    assert pmb.helpers.repo.hash(url, 8) == hash


def test_alpine_apkindex_path(args):
    func = pmb.helpers.repo.alpine_apkindex_path
    args.mirror_alpine = "http://dl-cdn.alpinelinux.org/alpine/"
    ret = args.work + "/cache_apk_armhf/APKINDEX.30e6f5af.tar.gz"
    assert func(args, "testing", "armhf") == ret
