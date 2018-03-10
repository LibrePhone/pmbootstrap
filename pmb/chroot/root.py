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
         auto_init=True, return_stdout=False, check=True, env={}):
    """
    Run a command inside a chroot as root.

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
    # Initialize chroot
    chroot = args.work + "/chroot_" + suffix
    if not auto_init and not os.path.islink(chroot + "/bin/sh"):
        raise RuntimeError("Chroot does not exist: " + chroot)
    if auto_init:
        pmb.chroot.init(args, suffix)

    # Readable log message (without all the escaping)
    msg = "(" + suffix + ") % "
    for key, value in env.items():
        msg += key + "=" + value + " "
    if working_dir != "/":
        msg += "cd " + working_dir + "; "
    msg += " ".join(cmd)

    # Merge env with defaults into env_all
    env_all = {"CHARSET": "UTF-8",
               "HISTFILE": "~/.ash_history",
               "PATH": pmb.config.chroot_path,
               "SHELL": "/bin/ash",
               "TERM": "xterm"}
    for key, value in env.items():
        env_all[key] = value

    # Build the command in steps and run it, e.g.:
    # cmd: ["echo", "test"]
    # cmd_chroot: ["/sbin/chroot", "/..._native", "/bin/sh", "-c", "echo test"]
    # cmd_sudo: ["sudo", "env", "-i", "sh", "-c", "PATH=... /sbin/chroot ..."]
    executables = executables_absolute_path()
    cmd_chroot = [executables["chroot"], chroot, "/bin/sh", "-c",
                  pmb.helpers.run.flat_cmd(cmd, working_dir)]
    cmd_sudo = ["sudo", "env", "-i", executables["sh"], "-c",
                pmb.helpers.run.flat_cmd(cmd_chroot, env=env_all)]
    return pmb.helpers.run.core(args, cmd_sudo, msg, log, return_stdout, check)
