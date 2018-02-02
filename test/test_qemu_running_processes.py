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

"""
This file runs various installations and boots into them with Qemu, then checks
via SSH if expected processes are running.

We use an extra config file (based on ~/.config/pmbootstrap.cfg), because we
need to change it a lot (e.g. UI, username, ...).
"""

import os
import pytest
import sys
import shutil
import shlex
import time
import logging

# Import from parent directory
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.append(pmb_src)
import pmb.chroot.apk_static
import pmb.parse.apkindex
import pmb.helpers.logging
import pmb.helpers.run
import pmb.parse.bootimg


@pytest.fixture
def args(request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def ssh_create_askpass_script(args):
    """Create /tmp/y.sh, which we need to automatically login via SSH."""
    with open(args.work + "/chroot_native/tmp/y.sh", "w") as handle:
        handle.write("#!/bin/sh\necho y\n")
    pmb.chroot.root(args, ["chmod", "+x", "/tmp/y.sh"])


def pmbootstrap_run(args, config, parameters, background=False):
    """Execute pmbootstrap.py with a test pmbootstrap.conf."""
    return pmb.helpers.run.user(args, ["./pmbootstrap.py", "-c", config] +
                                parameters, working_dir=pmb_src,
                                background=background)


def pmbootstrap_yes(args, config, parameters):
    """
    Execute pmbootstrap.py with a test pmbootstrap.conf, and pipe "yes"
    into it (so we can do a fully automated installation, using "y" as
    password everywhere).
    """
    command = "yes | ./pmbootstrap.py -c " + shlex.quote(config)
    for parameter in parameters:
        command += " " + shlex.quote(parameter)
    return pmb.helpers.run.user(args, ["/bin/sh", "-c", command],
                                working_dir=pmb_src)


class Qemu(object):
    def __init__(self, request):
        self.process = None
        request.addfinalizer(self.terminate)

    def terminate(self):
        if self.process:
            self.process.terminate()
        else:
            print("WARNING: The Qemu process wasn't set, so it could not be"
                  " terminated.")

    def run(self, args, tmpdir, ui="none"):
        # Copy and adjust user's pmbootstrap.cfg
        config = str(tmpdir) + "/pmbootstrap.cfg"
        shutil.copyfile(os.path.expanduser("~") + "/.config/pmbootstrap.cfg",
                        config)
        pmbootstrap_run(args, config, ["config", "device", "qemu-amd64"])
        pmbootstrap_run(args, config, ["config", "extra_packages", "none"])
        pmbootstrap_run(args, config, ["config", "user", "testuser"])
        pmbootstrap_run(args, config, ["config", "ui", ui])
        pmbootstrap_run(args, config, ["config", "qemu_native_mesa_driver", "dri-swrast"])

        # Prepare native chroot
        pmbootstrap_run(args, config, ["-y", "zap"])
        pmb.chroot.apk.install(args, ["openssh-client"])
        ssh_create_askpass_script(args)

        # Create and run system image
        pmbootstrap_yes(args, config, ["install", "--no-fde"])
        self.process = pmbootstrap_run(args, config, ["qemu", "--display",
                                                      "none"], background=True)
        logging.info("(test) wait 90s until the VM booted up")
        time.sleep(90)


@pytest.fixture
def qemu(request):
    return Qemu(request)


def ssh_run(args, command):
    """
    Run a command in the Qemu VM on localhost via SSH.

    :param command: flat string of the command to execute, e.g. "ps au"
    :returns: the result from the SSH server
    """
    ret = pmb.chroot.user(args, ["SSH_ASKPASS=/tmp/y.sh", "DISPLAY=", "ssh",
                                 "-o", "UserKnownHostsFile=/dev/null",
                                 "-o", "StrictHostKeyChecking=no",
                                 "-p", "2222", "testuser@localhost", "--",
                                 command],
                          return_stdout=True)
    return ret


def is_running(args, programs):
    """
    Simple check that looks for program names in the output of "ps ax".
    This is error-prone, only use it with programs that have a unique name.
    """
    all = ssh_run(args, "ps ax")
    ret = True
    for program in programs:
        if program in all:
            continue
        print(program + ": not found in 'ps ax'!")
        ret = False
    return ret


def test_xfce4(args, tmpdir, qemu):
    qemu.run(args, tmpdir, "xfce4")
    assert is_running(args, ["xfce4-session", "xfdesktop", "xfce4-panel",
                             "Thunar", "dbus-daemon", "xfwm4"])

    # self-test of is_running()
    assert is_running(args, ["invalid-process"]) is False


def test_plasma_mobile(args, tmpdir, qemu):
    # NOTE: Once we have plasma mobile running properly without GL, we can check
    # for more processes
    qemu.run(args, tmpdir, "plasma-mobile")
    assert is_running(args, ["polkitd"])
