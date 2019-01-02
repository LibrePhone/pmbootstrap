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
import errno
import json
import logging
import os
import pmb.chroot
import pmb.config
import pmb.chroot.apk

""" Packages for foreign architectures (e.g. armhf) get built in chroots
    running with QEMU. While this works, it is painfully slow. So we speed it
    up by using distcc to let cross compilers running in the native chroots do
    the heavy lifting.

    This file sets up an SSH server in the native chroot, which will then be
    used by the foreign arch chroot to communicate with the distcc daemon. We
    make sure that only the foreign arch chroot can connect to the sshd by only
    listening on localhost, as well as generating dedicated ssh keys.

    Using the SSH server instead of running distccd directly is a security
    measure. Distccd does not authenticate its clients and would therefore
    allow any process of the host system (not related to pmbootstrap) to
    execute compilers in the native chroot. By modifying the compiler's options
    or sending malicious data to the compiler, it is likely that the process
    can gain remote code execution [1]. That way, a compromised, but sandboxed
    process could gain privilege escalation.

    [1]: <https://github.com/distcc/distcc/issues/155#issuecomment-374014645>
"""


def init_server(args):
    """
    Install dependencies and generate keys for the server.
    """
    # Install dependencies
    pmb.chroot.apk.install(args, ["arch-bin-masquerade", "distcc",
                                  "openssh-server"])

    # Config folder (nothing to do if existing)
    dir = "/home/pmos/.distcc-sshd"
    dir_outside = args.work + "/chroot_native" + dir
    if os.path.exists(dir_outside):
        return

    # Generate keys
    logging.info("(native) generate distcc-sshd server keys")
    pmb.chroot.user(args, ["mkdir", "-p", dir + "/etc/ssh"])
    pmb.chroot.user(args, ["ssh-keygen", "-A", "-f", dir])


def init_client(args, suffix):
    """
    Install dependencies and generate keys for the client.
    """
    # Install dependencies
    pmb.chroot.apk.install(args, ["arch-bin-masquerade", "distcc",
                                  "openssh-client"], suffix)

    # Public key path (nothing to do if existing)
    pub = "/home/pmos/id_ed25519.pub"
    pub_outside = args.work + "/chroot_" + suffix + pub
    if os.path.exists(pub_outside):
        return

    # Generate keys
    logging.info("(" + suffix + ") generate distcc-sshd client keys")
    pmb.chroot.user(args, ["ssh-keygen", "-t", "ed25519", "-N", "",
                           "-f", "/home/pmos/.ssh/id_ed25519"], suffix)
    pmb.chroot.user(args, ["cp", "/home/pmos/.ssh/id_ed25519.pub", pub],
                    suffix)


def configure_authorized_keys(args, suffix):
    """
    Exclusively allow one foreign arch chroot to access the sshd.
    """
    auth = "/home/pmos/.distcc-sshd/authorized_keys"
    auth_outside = args.work + "/chroot_native/" + auth
    pub = "/home/pmos/id_ed25519.pub"
    pub_outside = args.work + "/chroot_" + suffix + pub
    pmb.helpers.run.root(args, ["cp", pub_outside, auth_outside])


def configure_cmdlist(args, arch):
    """
    Create a whitelist of all the cross compiler wrappers.

    Distcc 3.3 and above requires such a whitelist, or else it will only run
    with the --make-me-a-botnet parameter (even in ssh mode).
    """
    dir = "/home/pmos/.distcc-sshd"
    with open(args.work + "/chroot_native/tmp/cmdlist", "w") as handle:
        for cmd in ["c++", "cc", "cpp", "g++", "gcc"]:
            cmd_full = "/usr/lib/arch-bin-masquerade/" + arch + "/" + cmd
            handle.write(cmd_full + "\n")
    pmb.chroot.root(args, ["mv", "/tmp/cmdlist", dir + "/cmdlist"])
    pmb.chroot.user(args, ["cat", dir + "/cmdlist"])


def configure_distccd_wrapper(args):
    """
    Wrap distccd in a shell script, so we can pass the compiler whitelist and
    set the verbose flag (when pmbootstrap is running with --verbose).
    """
    dir = "/home/pmos/.distcc-sshd"
    with open(args.work + "/chroot_native/tmp/wrapper", "w") as handle:
        handle.write("#!/bin/sh\n"
                     "export DISTCC_CMDLIST='" + dir + "/cmdlist'\n"
                     "distccd --log-file /home/pmos/distccd.log --nice 19")
        if args.verbose:
            handle.write(" --verbose")
        handle.write(" \"$@\"\n")
    pmb.chroot.root(args, ["mv", "/tmp/wrapper", dir + "/distccd"])
    pmb.chroot.user(args, ["cat", dir + "/distccd"])
    pmb.chroot.root(args, ["chmod", "+x", dir + "/distccd"])


def configure_sshd(args):
    """
    Configure the SSH daemon in the native chroot.
    """
    dir = "/home/pmos/.distcc-sshd"
    config = """AllowAgentForwarding no
                AllowTcpForwarding no
                AuthorizedKeysFile /home/pmos/.distcc-sshd/authorized_keys
                HostKey /home/pmos/.distcc-sshd/etc/ssh/ssh_host_ed25519_key
                ListenAddress 127.0.0.1
                PasswordAuthentication no
                PidFile /home/pmos/.distcc-sshd/sshd.pid
                Port """ + args.port_distccd + """
                X11Forwarding no"""

    with open(args.work + "/chroot_native/tmp/cfg", "w") as handle:
        for line in config.split("\n"):
            handle.write(line.lstrip() + "\n")
    pmb.chroot.root(args, ["mv", "/tmp/cfg", dir + "/sshd_config"])
    pmb.chroot.user(args, ["cat", dir + "/sshd_config"])


def get_running_pid(args):
    """
    :returns: the running distcc-sshd's pid as integer or None
    """
    # PID file must exist
    pidfile = "/home/pmos/.distcc-sshd/sshd.pid"
    pidfile_outside = args.work + "/chroot_native" + pidfile
    if not os.path.exists(pidfile_outside):
        return None

    # Verify, if it still exists by sending a kill signal
    with open(pidfile_outside, "r") as handle:
        pid = int(handle.read()[:-1])
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:  # no such process
            pmb.helpers.run.root(args, ["rm", pidfile_outside])
            return None
    return pid


def get_running_parameters(args):
    """
    Get the parameters of the currently running distcc-sshd instance.

    :returns: a dictionary in the form of
              {"arch": "armhf", "port": 1234, "verbose": False}
              If the information can not be read, "arch" is set to "unknown"
    """
    # Return defaults
    path = args.work + "/chroot_native/tmp/distcc_sshd_parameters"
    if not os.path.exists(path):
        return {"arch": "unknown", "port": 0, "verbose": False}

    # Parse the file as JSON
    with open(path, "r") as handle:
        return json.loads(handle.read())


def set_running_parameters(args, arch):
    """
    Set the parameters of the currently running distcc-sshd instance.
    """
    parameters = {"arch": arch,
                  "port": args.port_distccd,
                  "verbose": args.verbose}

    path = args.work + "/chroot_native/tmp/distcc_sshd_parameters"
    with open(path, "w") as handle:
        json.dump(parameters, handle)


def is_running_with_same_parameters(args, arch):
    """
    Check whether we can use the already running distcc-sshd instance with our
    current set of parameters. In case we can use it directly, we save some
    time, otherwise we need to stop it, configure it again, and start it once
    more.
    """
    if not get_running_pid(args):
        return False

    parameters = get_running_parameters(args)
    return (parameters["arch"] == arch and
            parameters["port"] == args.port_distccd and
            parameters["verbose"] == args.verbose)


def stop(args):
    """
    Kill the sshd process (by using its pid).
    """
    pid = get_running_pid(args)
    if not pid:
        return

    parameters = get_running_parameters(args)
    logging.info("(native) stop distcc-sshd (" + parameters["arch"] + ")")
    pmb.chroot.user(args, ["kill", str(pid)])


def start(args, arch):
    """
    Set up a new distcc-sshd instance or use an already running one.
    """
    if is_running_with_same_parameters(args, arch):
        return
    stop(args)

    # Initialize server and client
    suffix = "buildroot_" + arch
    init_server(args)
    init_client(args, suffix)

    logging.info("(native) start distcc-sshd (" + arch + ") on 127.0.0.1:" +
                 args.port_distccd)

    # Configure server parameters (arch, port, verbose)
    configure_authorized_keys(args, suffix)
    configure_distccd_wrapper(args)
    configure_cmdlist(args, arch)
    configure_sshd(args)

    # Run
    dir = "/home/pmos/.distcc-sshd"
    pmb.chroot.user(args, ["/usr/sbin/sshd", "-f", dir + "/sshd_config",
                           "-E", dir + "/log.txt"])
    set_running_parameters(args, arch)
