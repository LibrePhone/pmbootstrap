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
import time
import pytest

# Import from parent directory
sys.path.insert(0, os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.helpers.git
import pmb.helpers.logging
import pmb.parse.version


@pytest.fixture
def args(request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_file_is_older_than(args, tmpdir):
    # Create a file last modified 10s ago
    tempfile = str(tmpdir) + "/test"
    pmb.helpers.run.user(args, ["touch", tempfile])
    past = time.time() - 10
    os.utime(tempfile, (-1, past))

    # Check the bounds
    func = pmb.helpers.file.is_older_than
    assert func(tempfile, 9) is True
    assert func(tempfile, 10) is True
    assert func(tempfile, 11) is False
