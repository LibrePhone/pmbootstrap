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
This file tests functions from pmb.helpers.run_core
"""

import os
import sys
import pytest

# Import from parent directory
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.append(pmb_src)
import pmb.helpers.run_core


@pytest.fixture
def args(request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_sanity_checks():
    func = pmb.helpers.run_core.sanity_checks

    # Invalid output
    with pytest.raises(RuntimeError) as e:
        func("invalid-output")
    assert str(e.value).startswith("Invalid output value")

    # Background and check
    func("background", check=None)
    for check in [True, False]:
        with pytest.raises(RuntimeError) as e:
            func("background", check=check)
        assert str(e.value).startswith("Can't use check with")

    # output_return
    func("log", output_return=True)
    with pytest.raises(RuntimeError) as e:
        func("tui", output_return=True)
    assert str(e.value).startswith("Can't use output_return with")

    # kill_as_root
    func("log", kill_as_root=True)
    with pytest.raises(RuntimeError) as e:
        func("tui", kill_as_root=True)
    assert str(e.value).startswith("Can't use kill_as_root with")


def test_background(args):
    # Sleep in background
    process = pmb.helpers.run_core.background(args, ["sleep", "1"], "/")

    # Check if it is still running
    assert process.poll() is None


def test_foreground_pipe(args):
    func = pmb.helpers.run_core.foreground_pipe
    cmd = ["echo", "test"]

    # Normal run
    assert func(args, cmd) == (0, "")

    # Return output
    assert func(args, cmd, output_return=True) == (0, "test\n")

    # Kill with output timeout
    cmd = ["sh", "-c", "echo first; sleep 2; echo second"]
    args.timeout = 0.3
    ret = func(args, cmd, output_return=True, output_timeout=True)
    assert ret == (-9, "first\n")

    # Kill with output timeout as root
    cmd = ["sudo", "sh", "-c", "printf first; sleep 2; printf second"]
    args.timeout = 0.3
    ret = func(args, cmd, output_return=True, output_timeout=True,
               kill_as_root=True)
    assert ret == (-9, "first")

    # Finish before timeout
    cmd = ["sh", "-c", "echo first; sleep 0.1; echo second; sleep 0.1;"
           "echo third; sleep 0.1; echo fourth"]
    args.timeout = 0.2
    ret = func(args, cmd, output_return=True, output_timeout=True)
    assert ret == (0, "first\nsecond\nthird\nfourth\n")


def test_foreground_tui():
    func = pmb.helpers.run_core.foreground_tui
    assert func(["echo", "test"]) == 0


def test_core(args):
    # Background
    func = pmb.helpers.run_core.core
    msg = "test"
    process = func(args, msg, ["sleep", "1"], output="background")
    assert process.poll() is None

    # Foreground (TUI)
    ret = func(args, msg, ["echo", "test"], output="tui")
    assert ret == 0

    # Foreground (pipe)
    ret = func(args, msg, ["echo", "test"], output="log")
    assert ret == 0

    # Return output
    ret = func(args, msg, ["echo", "test"], output="log", output_return=True)
    assert ret == "test\n"

    # Check the return code
    with pytest.raises(RuntimeError) as e:
        func(args, msg, ["false"], output="log")
    assert str(e.value).startswith("Command failed:")

    # Kill with timeout
    args.timeout = 0.2
    with pytest.raises(RuntimeError) as e:
        func(args, msg, ["sleep", "1"], output="log")
    assert str(e.value).startswith("Command failed:")
