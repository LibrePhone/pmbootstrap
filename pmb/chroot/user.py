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
import pmb.chroot.root
import pmb.helpers.run


def user(args, cmd, suffix="native", working_dir="/", log=True,
         auto_init=True, return_stdout=False, check=True, env={}):
    """
    Run a command inside a chroot as "user". We always use the BusyBox
    implementation of 'su', because other implementations may override the PATH
    environment variable (#1071).

    :param cmd: command as list, e.g. ["echo", "string with spaces"]
    :param suffix: of the chroot to execute code in
    :param working_dir: path inside chroot where the command should run
    :param log: when set to true, redirect all output to the logfile
    :param auto_init: automatically initialize the chroot
    :param return_stdout: write stdout to a buffer and return it as string when
                          the command is through
    :param check: raise an exception, when the command fails
    :param env: dict of environment variables to be passed to the command, e.g.
                {"JOBS": "5"}
    :returns: * stdout when return_stdout is True
              * None otherwise
    """
    flat_cmd = pmb.helpers.run.flat_cmd(cmd, env=env)
    cmd = ["busybox", "su", "pmos", "-c", flat_cmd]
    return pmb.chroot.root(args, cmd, suffix, working_dir, log,
                           auto_init, return_stdout, check)


def exists(args, username, suffix="native"):
    """
    Checks if username exists in the system

    :param username: User name
    :returns: bool
    """
    output = pmb.chroot.root(args, ["getent", "passwd", username],
                             suffix, return_stdout=True, check=False)
    return (output is not None)
