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
import pytest

# Import from parent directory
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, pmb_src)
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
    cmds = {"test\n": ["echo", "test"],
            "test && test\n": ["echo", "test", "&&", "test"],
            "test ; test\n": ["echo", "test", ";", "test"],
            "'test\"test\\'\n": ["echo", "'test\"test\\'"],
            "*\n": ["echo", "*"],
            "$PWD\n": ["echo", "$PWD"],
            "hello world\n": ["printf", "%s world\n", "hello"]}
    for expected, cmd in cmds.items():
        copy = list(cmd)
        core = pmb.helpers.run_core.core(args, str(cmd), cmd,
                                         output_return=True)
        assert expected == core
        assert cmd == copy

        user = pmb.helpers.run.user(args, cmd, output_return=True)
        assert expected == user
        assert cmd == copy

        root = pmb.helpers.run.root(args, cmd, output_return=True)
        assert expected == root
        assert cmd == copy

        chroot_root = pmb.chroot.root(args, cmd, output_return=True)
        assert expected == chroot_root
        assert cmd == copy

        chroot_user = pmb.chroot.user(args, cmd, output_return=True)
        assert expected == chroot_user
        assert cmd == copy


def test_shell_escape_env(args):
    key = "PMBOOTSTRAP_TEST_ENVIRONMENT_VARIABLE"
    value = "long value with spaces and special characters: '\"\\!$test"
    env = {key: value}
    cmd = ["sh", "-c", "env | grep " + key + " | grep -v SUDO_COMMAND"]
    ret = key + "=" + value + "\n"

    copy = list(cmd)
    func = pmb.helpers.run.user
    assert func(args, cmd, output_return=True, env=env) == ret
    assert cmd == copy

    func = pmb.helpers.run.root
    assert func(args, cmd, output_return=True, env=env) == ret
    assert cmd == copy

    func = pmb.chroot.root
    assert func(args, cmd, output_return=True, env=env) == ret
    assert cmd == copy

    func = pmb.chroot.user
    assert func(args, cmd, output_return=True, env=env) == ret
    assert cmd == copy


def test_flat_cmd_simple():
    func = pmb.helpers.run.flat_cmd
    cmd = ["echo", "test"]
    working_dir = None
    ret = "echo test"
    env = {}
    assert func(cmd, working_dir, env) == ret


def test_flat_cmd_wrap_shell_string_with_spaces():
    func = pmb.helpers.run.flat_cmd
    cmd = ["echo", "string with spaces"]
    working_dir = None
    ret = "echo 'string with spaces'"
    env = {}
    assert func(cmd, working_dir, env) == ret


def test_flat_cmd_wrap_env_simple():
    func = pmb.helpers.run.flat_cmd
    cmd = ["echo", "test"]
    working_dir = None
    ret = "JOBS=5 echo test"
    env = {"JOBS": "5"}
    assert func(cmd, working_dir, env) == ret


def test_flat_cmd_wrap_env_spaces():
    func = pmb.helpers.run.flat_cmd
    cmd = ["echo", "test"]
    working_dir = None
    ret = "JOBS=5 TEST='spaces string' echo test"
    env = {"JOBS": "5", "TEST": "spaces string"}
    assert func(cmd, working_dir, env) == ret
