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
import os
import shutil
import shlex

import pmb.config
import pmb.chroot
import pmb.chroot.binfmt
import pmb.helpers.run


def executables_absolute_path():
    """
    Get the absolute paths to the sh and chroot executables.
    """
    ret = {}
    for binary in ["sh", "chroot"]:
        path = shutil.which(binary, path=pmb.config.chroot_host_path)
        if not path:
            raise RuntimeError("Could not find the '" + binary +
                               "' executable. Make sure, that it is in" " your current user's PATH.")
        ret[binary] = path
    return ret


def root(args, cmd, suffix="native", working_dir="/", log=True,
         auto_init=True, return_stdout=False, check=True):
    """
    Run a command inside a chroot as root.

    :param log: When set to true, redirect all output to the logfile
    :param auto_init: Automatically initialize the chroot
    """
    # Get and verify chroot folder
    chroot = args.work + "/chroot_" + suffix
    if not auto_init and not os.path.islink(chroot + "/bin/sh"):
        raise RuntimeError("Chroot does not exist: " + chroot)

    if auto_init:
        pmb.chroot.init(args, suffix)

    # Run the args with sudo chroot, and with cleaned environment
    # variables
    executables = executables_absolute_path()
    for i in range(len(cmd)):
        cmd[i] = shlex.quote(cmd[i])
    cmd_inner_shell = ("cd " + shlex.quote(working_dir) + ";" +
                       " ".join(cmd))

    cmd_full = ["sudo", executables["sh"], "-c",
                "env -i" +  # unset all
                " CHARSET=UTF-8" +
                " PATH=" + pmb.config.chroot_path +
                " SHELL=/bin/ash" +
                " HISTFILE=~/.ash_history" +
                " " + executables["chroot"] +
                " " + chroot +
                " sh -c " + shlex.quote(cmd_inner_shell)
                ]

    # Generate log message
    log_message = "(" + suffix + ") % "
    if working_dir != "/":
        log_message += "cd " + working_dir + " && "
    log_message += " ".join(cmd)

    # Run the command
    return pmb.helpers.run.core(args, cmd_full, log_message, log,
                                return_stdout, check)
