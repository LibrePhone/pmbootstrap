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
import types
import time

# Import from parent directory
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.append(pmb_src)
import pmb.build
import pmb.helpers.logging
import pmb.helpers.repo


@pytest.fixture
def args(request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


@pytest.fixture
def args_fake_work_dir(request, tmpdir):
    args = types.SimpleNamespace()
    args.work = str(tmpdir)
    return args


def clear_timestamps_from_files(files):
    """
    Replace all last modified timestamps from pmb.helpers.repo.files() with
    None. The files-parameter gets changed in place.
    """
    for arch in files.keys():
        for file in files[arch].keys():
            files[arch][file] = None


def test_files_empty(args_fake_work_dir):
    args = args_fake_work_dir
    os.mkdir(args.work + "/packages")
    assert pmb.helpers.repo.files(args) == {}


def test_files_not_empty(args_fake_work_dir):
    args = args_fake_work_dir
    pkgs = args.work + "/packages"
    for dir in ["", "armhf", "x86_64"]:
        os.mkdir(pkgs + "/" + dir)
    open(pkgs + "/x86_64/test", "a").close()
    files = pmb.helpers.repo.files(args)
    clear_timestamps_from_files(files)
    assert files == {"armhf": {}, "x86_64": {"test": None}}


def test_files_diff(args_fake_work_dir):
    args = args_fake_work_dir
    # Create x86_64/test, x86_64/test2
    pkgs = args.work + "/packages"
    for dir in ["", "x86_64"]:
        os.mkdir(pkgs + "/" + dir)
    for file in ["x86_64/test", "x86_64/test2"]:
        open(pkgs + "/" + file, "a").close()

    # First snapshot
    first = pmb.helpers.repo.files(args)

    # Change: x86_64/test (set the lastmod timestamp 5 seconds in the future)
    mtime_old = os.path.getmtime(pkgs + "/x86_64/test")
    time_new = time.time() + 5
    os.utime(pkgs + "/x86_64/test", (time_new, time_new))
    mtime_new = os.path.getmtime(pkgs + "/x86_64/test")
    assert mtime_old != mtime_new

    # Create: aarch64/test3, x86_64/test4
    os.mkdir(pkgs + "/aarch64")
    open(pkgs + "/aarch64/test3", "a").close()
    open(pkgs + "/x86_64/test4", "a").close()

    diff = pmb.helpers.repo.diff(args, first)
    assert diff == ["aarch64/test3", "x86_64/test", "x86_64/test4"]


def test_hash():
    url = "https://nl.alpinelinux.org/alpine/edge/testing"
    hash = "865a153c"
    assert pmb.helpers.repo.hash(url, 8) == hash
