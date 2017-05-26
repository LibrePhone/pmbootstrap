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
#!/usr/bin/env python3
import os
import sys
import pytest

# Import from parent directory
sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.aportgen


@pytest.fixture
def args(tmpdir):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    setattr(args, "logfd", open("/dev/null", "a+"))
    yield args
    args.logfd.close()


def test_build(args):
    pmb.build.package(args, "hello-world", args.arch_native, True)


def test_build_armhf(args):
    """
    Build in armhf chroot, with cross-compiler through distcc.
    """
    pmb.build.package(args, "hello-world", "armhf", True)
