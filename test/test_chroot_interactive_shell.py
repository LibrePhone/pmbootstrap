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
import subprocess
import os


def test_chroot_interactive_shell():
    """
    Open a shell with 'pmbootstrap chroot' and pass 'echo hello_world\n' as stdin.
    """
    pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
    os.chdir(pmb_src)
    ret = subprocess.check_output(["./pmbootstrap.py", "-q", "chroot", "sh"],
                                  timeout=300, input="echo hello_world\n",
                                  universal_newlines=True,
                                  stderr=subprocess.STDOUT)
    assert ret == "hello_world\n"


def test_chroot_interactive_shell_user():
    """
    Open a shell with 'pmbootstrap chroot' as user, and test the resulting ID.
    """
    pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
    os.chdir(pmb_src)
    ret = subprocess.check_output(["./pmbootstrap.py", "-q", "chroot",
                                   "--user", "sh"], timeout=300, input="id -un",
                                  universal_newlines=True,
                                  stderr=subprocess.STDOUT)
    assert ret == "pmos\n"


def test_chroot_arguments():
    """
    Open a shell with 'pmbootstrap chroot' for every architecture, pass 'uname -m\n'
    as stdin and check the output
    """
    pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
    os.chdir(pmb_src)

    for arch in ["armhf", "aarch64", "x86_64"]:
        ret = subprocess.check_output(["./pmbootstrap.py", "-q", "chroot", "-b", arch,
                                       "sh"], timeout=300, input="uname -m\n",
                                      universal_newlines=True, stderr=subprocess.STDOUT)
        if arch == "armhf":
            assert ret == "armv7l\n"
        else:
            assert ret == arch + "\n"
