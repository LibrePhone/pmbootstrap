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


def get_pid(args):
    pidfile = args.work + "/chroot_native/home/user/distccd.pid"
    if not os.path.exists(pidfile):
        return None
    with open(pidfile, "r") as handle:
        lines = handle.readlines()
    return int(lines[0][:-1])


def is_running(args):
    # Get the PID
    pid = get_pid(args)
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
            return True


def start(args):
    if is_running(args):
        return
    pmb.chroot.apk.install(args, ["distcc", "gcc-cross-wrappers"])

    # Start daemon with cross-compiler in path
    arch = args.deviceinfo["arch"]
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
    logging.info("(native) start distccd (listen on 127.0.0.1:" +
                 args.port_distccd + ")")
    pmb.chroot.user(args, daemon)


def stop(args):
    if is_running(args):
        logging.info("(native) stop distccd")
        pmb.chroot.user(args, ["kill", str(get_pid(args))])
