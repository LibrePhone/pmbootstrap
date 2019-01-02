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
import pmb.chroot.root
import pmb.helpers.run


def user(args, cmd, suffix="native", working_dir="/", output="log",
         output_return=False, check=None, env={}, auto_init=True):
    """
    Run a command inside a chroot as "user". We always use the BusyBox
    implementation of 'su', because other implementations may override the PATH
    environment variable (#1071).

    :param env: dict of environment variables to be passed to the command, e.g.
                {"JOBS": "5"}
    :param auto_init: automatically initialize the chroot

    See pmb.helpers.run_core.core() for a detailed description of all other
    arguments and the return value.
    """
    if "HOME" not in env:
        env["HOME"] = "/home/pmos"

    flat_cmd = pmb.helpers.run.flat_cmd(cmd, env=env)
    cmd = ["busybox", "su", "pmos", "-c", flat_cmd]
    return pmb.chroot.root(args, cmd, suffix, working_dir, output,
                           output_return, check, {}, auto_init)


def exists(args, username, suffix="native"):
    """
    Checks if username exists in the system

    :param username: User name
    :returns: bool
    """
    output = pmb.chroot.root(args, ["getent", "passwd", username],
                             suffix, output_return=True, check=False)
    return len(output) > 0
