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
import pmb.aportgen
import pmb.config
import pmb.helpers.logging


@pytest.fixture
def args(tmpdir, request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_build(args):
    pmb.build.package(args, "hello-world", args.arch_native, True)


def test_build_cross(args):
    """
    Build in non-native chroot, with cross-compiler through distcc.
    """
    for arch in pmb.config.build_device_architectures:
        pmb.build.package(args, "hello-world", arch, True)
