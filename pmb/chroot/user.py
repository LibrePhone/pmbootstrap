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
import pmb.chroot.root


def user(args, cmd, suffix="native", working_dir="/", log=True,
         auto_init=True, return_stdout=False, check=True):
    """
    Run a command inside a chroot as "user"

    :param log: When set to true, redirect all output to the logfile
    :param auto_init: Automatically initialize the chroot
    """
    cmd = ["su", "pmos", "-c", " ".join(cmd)]
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
