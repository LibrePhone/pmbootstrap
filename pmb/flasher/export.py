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
import glob

import pmb.build
import pmb.chroot.apk
import pmb.config
import pmb.flasher


def export(args, flavor, folder):
    """
    Create convenience symlinks to the system image and boot files.
    """
    logging.info("Export symlinks to: " + folder)

    # File descriptions
    info = {
        "boot.img-" + flavor: "Fastboot compatible boot.img file,"
        " contains initramfs and kernel",
        "initramfs-" + flavor: "Initramfs",
        "uInitrd-" + flavor: "Initramfs, legacy u-boot image format",
        "uImage-" + flavor: "Kernel, legacy u-boot image format",
        "vmlinuz-" + flavor: "Linux kernel",
        args.device + ".img": "System partition",
    }

    # Generate a list of patterns
    path_native = args.work + "/chroot_native"
    path_boot = args.work + "/chroot_rootfs_" + args.device + "/boot"
    patterns = [path_boot + "/*-" + flavor,
                path_native + "/home/user/rootfs/" + args.device + ".img"]

    # Generate a list of files from the patterns
    files = []
    for pattern in patterns:
        files += glob.glob(pattern)

    # Iterate through all files
    for file in files:
        basename = os.path.basename(file)
        link = folder + "/" + basename

        # Display a readable message
        msg = " * " + basename
        if basename in info:
            msg += " (" + info[basename] + ")"
        logging.info(msg)

        if os.path.exists(link):
            if (os.path.islink(link) and
                    os.path.abspath(os.readlink(link)) == os.path.abspath(file)):
                continue
            raise RuntimeError("File exists: " + link)

        # Create the symlink
        pmb.helpers.run.user(args, ["ln", "-s", file, link])
