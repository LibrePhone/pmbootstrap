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
import pmb.parse.apkindex
import pmb.helpers.git


@pytest.fixture
def args():
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    setattr(args, "logfd", open("/dev/null", "a+"))
    yield args
    args.logfd.close()
    return args


def test_version(args):
    # clone official test file from apk-tools
    pmb.helpers.git.clone(args, "apk-tools")
    path = args.work + "/cache_git/apk-tools/test/version.data"

    mapping = {-1: "<", 0: "=", 1: ">"}
    with open(path) as handle:
        for line in handle:
            split = line.split(" ")
            a = split[0]
            b = split[2].rstrip()
            expected = split[1]

            # Alpine packages nowadays always have '-r' in their version
            if "-r" not in a or "-r" not in b:
                continue

            print(line.rstrip())
            try:
                result = pmb.parse.apkindex.compare_version(a, b)
                real = mapping[result]
            except TypeError:
                # FIXME: Bug in Python:
                # https://bugs.python.org/issue14894
                # When this happens in pmbootstrap, it will also raise the
                                # TypeError exception.
                continue
            assert(real == expected)
