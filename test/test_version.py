"""
Copyright 2018 Oliver Smith

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
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.append(pmb_src)
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


def test_version(args):
    # Fail after the first error or print a grand total of failures
    keep_going = False

    # Iterate over the version tests from apk-tools
    path = pmb_src + "/test/testdata/version/version.data"
    mapping = {-1: "<", 0: "=", 1: ">"}
    count = 0
    errors = []
    with open(path) as handle:
        for line in handle:
            split = line.split(" ")
            a = split[0]
            b = split[2].split("#")[0].rstrip()
            expected = split[1]
            print("(#" + str(count) + ") " + line.rstrip())
            result = pmb.parse.version.compare(a, b)
            real = mapping[result]

            count += 1
            if real != expected:
                if keep_going:
                    errors.append(line.rstrip() + " (got: '" + real + "')")
                else:
                    assert real == expected

    print("---")
    print("total: " + str(count))
    print("errors: " + str(len(errors)))
    print("---")
    for error in errors:
        print(error)
    assert errors == []
