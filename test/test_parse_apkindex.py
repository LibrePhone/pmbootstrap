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
import pytest
import sys

# Import from parent directory
sys.path.append(os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.parse.apkindex
import pmb.helpers.logging
import pmb.helpers.repo


@pytest.fixture
def args(tmpdir, request):
    import pmb.parse
    sys.argv = ["pmbootstrap", "init"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_read_any_index_highest_version(args, monkeypatch):
    # Return 3 fake "files" for pmb.helpers.repo.apkindex_files()
    def return_fake_files(*arguments):
        return ["0", "1", "2"]
    monkeypatch.setattr(pmb.helpers.repo, "apkindex_files",
                        return_fake_files)

    # Return fake index data for the "files"
    def return_fake_read(args, package, path, must_exist=True):
        return {"0": {"pkgname": "test", "version": "2"},
                "1": {"pkgname": "test", "version": "3"},
                "2": {"pkgname": "test", "version": "1"}}[path]
    monkeypatch.setattr(pmb.parse.apkindex, "read", return_fake_read)

    # Verify that it picks the highest version
    func = pmb.parse.apkindex.read_any_index
    assert func(args, "test")["version"] == "3"
