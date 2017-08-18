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
sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.helpers.logging
import pmb.helpers.other
import pmb.helpers.run


@pytest.fixture
def args(request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.details_to_stdout = True
    pmb.helpers.logging.init(args)
    return args


def test_get_folder_size(args, tmpdir):
    # Write five 2 KB files to tmpdir
    tmpdir = str(tmpdir)
    files = 5
    for i in range(files):
        pmb.helpers.run.user(args, ["dd", "if=/dev/zero", "of=" +
                                    tmpdir + "/" + str(i), "bs=1K",
                                    "count=2", "conv=notrunc"])

    # Check if the size is correct
    assert pmb.helpers.other.folder_size(args, tmpdir) == 20480
