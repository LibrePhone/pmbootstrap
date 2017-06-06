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
import os
import logging
import glob

import pmb.config
import pmb.chroot
import pmb.chroot.apk
import pmb.helpers.run


def init(args, suffix="native"):
    # Check if already initialized
    marker = "/var/local/pmbootstrap_chroot_build_init_done"
    if os.path.exists(args.work + "/chroot_" + suffix + marker):
        return

    # Initialize chroot, install packages
    pmb.chroot.apk.install(args, pmb.config.build_packages, suffix)

    # Fix permissions
    pmb.chroot.root(args, ["chmod", "-R", "a+rw",
                           "/var/cache/distfiles"], suffix)

    # Generate package signing keys
    chroot = args.work + "/chroot_" + suffix
    if not os.path.exists(chroot + "/home/user/.abuild/abuild.conf"):
        logging.info("(" + suffix + ") generate abuild keys")
        pmb.chroot.user(args, ["abuild-keygen", "-n", "-q", "-a"],
                        suffix)

        # Copy package signing key to /etc/apk/keys
        for key in glob.glob(chroot + "/home/user/.abuild/*.pub"):
            key = key[len(chroot):]
            pmb.chroot.root(args, ["cp", key, "/etc/apk/keys/"], suffix)

    # Add gzip wrapper, that converts '-9' to '-1'
    if not os.path.exists(chroot + "/usr/local/bin/gzip"):
        with open(chroot + "/tmp/gzip_wrapper.sh", "w") as handle:
            content = """
                #!/bin/sh
                # Simple wrapper, that converts -9 flag for gzip to -1 for speed
                # improvement with abuild. FIXME: upstream to abuild with a flag!
                args=""
                for arg in "$@"; do
                    [ "$arg" == "-9" ] && arg="-1"
                    args="$args $arg"
                done
                /bin/gzip $args
            """
            lines = content.split("\n")[1:]
            for i in range(len(lines)):
                lines[i] = lines[i][16:]
            handle.write("\n".join(lines))
        pmb.chroot.root(args, ["cp", "/tmp/gzip_wrapper.sh", "/usr/local/bin/gzip"],
                        suffix)
        pmb.chroot.root(args, ["chmod", "+x", "/usr/local/bin/gzip"], suffix)

    # Add user to group abuild
    pmb.chroot.root(args, ["adduser", "user", "abuild"], suffix)

    # abuild.conf: Don't clean the build folder after building, so we can
    # inspect it afterwards for debugging
    pmb.chroot.root(args, ["sed", "-i", "-e", "s/^CLEANUP=.*/CLEANUP=''/",
                           "/etc/abuild.conf"], suffix)

    # Mark the chroot as initialized
    pmb.chroot.root(args, ["touch", marker], suffix)
