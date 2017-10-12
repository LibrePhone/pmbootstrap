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
import configparser
import errno
import logging
import os
import pmb.chroot
import pmb.config
import pmb.chroot.apk


def get_running_pid(args):
    """
    :returns: the running distccd's pid as integer or None
    """
    pidfile = args.work + "/chroot_native/home/pmos/distccd.pid"
    if not os.path.exists(pidfile):
        return None
    with open(pidfile, "r") as handle:
        lines = handle.readlines()
    return int(lines[0][:-1])


def get_running_info(args):
    """
    :returns: A dictionary in the form of {"arch": .., "cmdline": "" }. arch is
              the architecture (e.g. "armhf" or "aarch64"), and "cmdline" is the
              saved value from the generate_cmdline() list, joined on space.
              If the information can not be read, "arch" and "cmdline" are set to
              "unknown".
    The arch is used to print a nice stop message, the full cmdline is used to
    check whether distccd needs to be restartet (e.g. because the arch has been
    changed, or the verbose flag).
    """
    info = configparser.ConfigParser()
    path = args.work + "/chroot_native/tmp/distccd_running_info"
    if os.path.exists(path):
        info.read(path)
    else:
        info["distccd"] = {}
        info["distccd"]["arch"] = "unknown"
        info["distccd"]["cmdline"] = "unknown"
    return info["distccd"]


def is_running(args):
    """
    :returns: When not running: None
              When running: result from get_running_info()
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
            pmb.chroot.root(args, ["rm", "/home/pmos/distccd.pid"])
            return False
        elif err.errno == errno.EPERM:  # access denied
            return get_running_info(args)


def generate_cmdline(args, arch):
    """
    :returns: a dictionary suitable for pmb.chroot.user(), to start the distccd
              with the cross-compiler in the path and all options set.
    """
    path = "/usr/lib/gcc-cross-wrappers/" + arch + "/bin:" + pmb.config.chroot_path
    ret = ["PATH=" + path,
           "distccd",
           "--pid-file", "/home/pmos/distccd.pid",
           "--listen", "127.0.0.1",
           "--allow", "127.0.0.1",
           "--port", args.port_distccd,
           "--log-file", "/home/pmos/distccd.log",
           "--jobs", args.jobs,
           "--nice", "19",
           "--job-lifetime", "60",
           "--daemon"
           ]
    if args.verbose:
        ret.append("--verbose")
    return ret


def start(args, arch):
    # Skip when already running with the same cmdline
    cmdline = generate_cmdline(args, arch)
    info = is_running(args)
    if info and info["cmdline"] == " ".join(cmdline):
        return
    stop(args)
    pmb.chroot.apk.install(args, ["distcc", "gcc-cross-wrappers"])

    # Start daemon with cross-compiler in path
    logging.info("(native) start distccd (" + arch + ") on 127.0.0.1:" +
                 args.port_distccd)
    pmb.chroot.user(args, cmdline)

    # Write down the arch and cmdline (which also contains the relevant
    # environment variables, /proc/$pid/cmdline does not!)
    info = configparser.ConfigParser()
    info["distccd"] = {}
    info["distccd"]["arch"] = arch
    info["distccd"]["cmdline"] = " ".join(cmdline)
    with open(args.work + "/chroot_native/tmp/distccd_running_info", "w") as handle:
        info.write(handle)


def stop(args):
    info = is_running(args)
    if info:
        logging.info("(native) stop distccd (" + info["arch"] + ")")
        pmb.chroot.user(args, ["kill", str(get_running_pid(args))])
