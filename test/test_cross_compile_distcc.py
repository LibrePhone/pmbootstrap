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
sys.path.insert(0, os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.build
import pmb.chroot.distccd
import pmb.helpers.logging


@pytest.fixture
def args(tmpdir, request):
    import pmb.parse
    sys.argv = ["pmbootstrap", "init"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_cross_compile_distcc(args):
    # Delete old distccd log
    pmb.chroot.distccd.stop(args)
    distccd_log = args.work + "/chroot_native/home/pmos/distccd.log"
    if os.path.exists(distccd_log):
        pmb.helpers.run.root(args, ["rm", distccd_log])

    # Force usage of distcc (no fallback, no ccache)
    args.verbose = True
    args.ccache = False
    args.distcc_fallback = False

    # Compile, print distccd and sshd logs on error
    try:
        pmb.build.package(args, "hello-world", arch="armhf", force=True)
    except RuntimeError:
        print("distccd log:")
        pmb.helpers.run.user(args, ["cat", distccd_log], output="stdout",
                             check=False)
        print("sshd log:")
        sshd_log = args.work + "/chroot_native/home/pmos/.distcc-sshd/log.txt"
        pmb.helpers.run.root(args, ["cat", sshd_log], output="stdout",
                             check=False)
        raise
