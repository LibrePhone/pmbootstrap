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
import logging
import os
import glob

import pmb.build
import pmb.chroot.apk
import pmb.config
import pmb.flasher
import pmb.helpers.file


def symlinks(args, flavor, folder):
    """
    Create convenience symlinks to the rootfs and boot files.
    """

    # File descriptions
    info = {
        "boot.img-" + flavor: "Fastboot compatible boot.img file,"
        " contains initramfs and kernel",
        "blob-" + flavor: "Asus boot blob for TF101",
        "initramfs-" + flavor: "Initramfs",
        "initramfs-" + flavor + "-extra": "Extra initramfs files in /boot",
        "uInitrd-" + flavor: "Initramfs, legacy u-boot image format",
        "uImage-" + flavor: "Kernel, legacy u-boot image format",
        "vmlinuz-" + flavor: "Linux kernel",
        args.device + ".img": "Rootfs with partitions for /boot and /",
        args.device + "-boot.img": "Boot partition image",
        args.device + "-root.img": "Root partition image",
        "pmos-" + args.device + ".zip": "Android recovery flashable zip",
    }

    # Generate a list of patterns
    path_native = args.work + "/chroot_native"
    path_boot = args.work + "/chroot_rootfs_" + args.device + "/boot"
    path_buildroot = args.work + "/chroot_buildroot_" + args.deviceinfo["arch"]
    patterns = [path_boot + "/*-" + flavor,
                path_boot + "/*-" + flavor + "-extra",
                path_native + "/home/pmos/rootfs/" + args.device + ".img",
                path_native + "/home/pmos/rootfs/" + args.device + "-boot.img",
                path_native + "/home/pmos/rootfs/" + args.device + "-root.img",
                path_buildroot +
                "/var/lib/postmarketos-android-recovery-installer/pmos-" +
                args.device + ".zip"]

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

        pmb.helpers.file.symlink(args, file, link)
