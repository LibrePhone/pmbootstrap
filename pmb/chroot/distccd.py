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
import logging
import os
import errno
import pmb.chroot
import pmb.config
import pmb.chroot.apk


def get_running_pid(args):
    pidfile = args.work + "/chroot_native/home/user/distccd.pid"
    if not os.path.exists(pidfile):
        return None
    with open(pidfile, "r") as handle:
        lines = handle.readlines()
    return int(lines[0][:-1])


def get_running_arch(args):
    """
    :returns: the architecture string of the running distccd process (eg.
              "armhf" or "aarch64") or "unknown" if the file does not exist.
    """
    file = args.work + "/chroot_native/tmp/distccd_running_arch"
    if not os.path.exists(file):
        return "unknown"
    with open(file, "r") as handle:
        lines = handle.readlines()
    return lines[0][:-1]


def is_running(args):
    """
    :returns: When not running: None
              When running: the arch string, e.g. "armhf"
    """
    # Get the PID
    pid = get_running_pid(args)
    if not pid:
        return False

    # Verify, if it still exists by sending a kill signal
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:  # no such process
            pmb.chroot.root(args, ["rm", "/home/user/distccd.pid"])
            return False
        elif err.errno == errno.EPERM:  # access denied
            return get_running_arch(args)


def start(args, arch):
    if is_running(args) == arch:
        return
    stop(args)
    pmb.chroot.apk.install(args, ["distcc", "gcc-cross-wrappers"])

    # Start daemon with cross-compiler in path
    path = "/usr/lib/gcc-cross-wrappers/" + arch + "/bin:" + pmb.config.chroot_path
    daemon = ["PATH=" + path,
              "distccd",
              "--pid-file", "/home/user/distccd.pid",
              "--listen", "127.0.0.1",
              "--allow", "127.0.0.1",
              "--port", args.port_distccd,
              "--log-file", "/home/user/distccd.log",
              "--jobs", args.jobs,
              "--nice", "19",
              "--job-lifetime", "60",
              "--daemon"
              ]
    logging.info(
        "(native) start distccd (" +
        arch +
        ") on 127.0.0.1:" +
        args.port_distccd)
    pmb.chroot.user(args, daemon)

    # Write down the running architecture
    with open(args.work + "/chroot_native/tmp/distccd_running_arch", "w") as handle:
        handle.write(arch + "\n")


def stop(args):
    arch = is_running(args)
    if arch:
        logging.info("(native) stop distccd (" + arch + ")")
        pmb.chroot.user(args, ["kill", str(get_running_pid(args))])
