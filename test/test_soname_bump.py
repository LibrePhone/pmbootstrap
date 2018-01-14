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

"""
This file uses pmb.helper.pkgrel_bump to check if the aports need a pkgrel bump
for any package, caused by a soname bump. Example: A new libressl/openssl
version was released, which increased the soname version, and now all packages
that link against it, need to be rebuilt.
"""

import os
import pytest
import sys

# Import from parent directory
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.append(pmb_src)
import pmb.helpers.pkgrel_bump
import pmb.helpers.logging


@pytest.fixture
def args(request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_soname_bump(args):
    if pmb.helpers.pkgrel_bump.auto(args, True):
        raise RuntimeError("One or more packages need to be rebuilt, because"
                           " a library they link against had an incompatible"
                           " upgrade (soname bump). Run 'pmbootstrap"
                           " pkgrel_bump --auto' to automatically increase the"
                           " pkgrel in order to trigger a rebuild. If this"
                           " test case failed during a pull request, the issue"
                           " needs to be fixed on the 'master' branch first,"
                           " then rebase your PR on 'master' afterwards.")
