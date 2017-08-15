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
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.append(pmb_src)
import pmb.chroot.root
import pmb.chroot.user
import pmb.helpers.run
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


def test_shell_escape(args):
    cmds = {
        "test\n": ["echo", "test"],
        "test && test\n": ["echo", "test", "&&", "test"],
        "test ; test\n": ["echo", "test", ";", "test"],
        "'test\"test\\'\n": ["echo", "'test\"test\\'"],
        "*\n": ["echo", "*"],
        "$PWD\n": ["echo", "$PWD"],
    }
    for expected, cmd in cmds.items():
        core = pmb.helpers.run.core(args, cmd, "test", True, True)
        assert expected == core

        user = pmb.helpers.run.user(args, cmd, return_stdout=True)
        assert expected == user

        root = pmb.helpers.run.root(args, cmd, return_stdout=True)
        assert expected == root

        chroot_root = pmb.chroot.root(args, cmd, return_stdout=True)
        assert expected == chroot_root

        chroot_user = pmb.chroot.user(args, cmd, return_stdout=True)
        assert expected == chroot_user
