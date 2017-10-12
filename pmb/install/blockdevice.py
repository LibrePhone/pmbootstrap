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
import pmb.helpers.mount
import pmb.install.losetup
import pmb.helpers.cli
import pmb.config


def mount_sdcard(args):
    # Sanity checks
    if args.deviceinfo["external_disk_install"] != "true":
        raise RuntimeError("According to the deviceinfo, this device does"
                           " not support a sdcard installation.")
    if not os.path.exists(args.sdcard):
        raise RuntimeError("The sdcard device does not exist: " +
                           args.sdcard)
    for path in glob.glob(args.sdcard + "*"):
        if pmb.helpers.mount.ismount(path):
            raise RuntimeError(path + " is mounted! We will not attempt"
                               " to format this!")
    if not pmb.helpers.cli.confirm(args, "EVERYTHING ON " + args.sdcard +
                                   " WILL BE ERASED! CONTINUE?"):
        raise RuntimeError("Aborted.")

    logging.info("(native) mount /dev/install (host: " + args.sdcard + ")")
    pmb.helpers.mount.bind_blockdevice(args, args.sdcard,
                                       args.work + "/chroot_native/dev/install")


def create_and_mount_image(args, size):
    """
    Create a new image file, and mount it as /dev/install.

    :param size: of the whole image in bytes
    """
    # Short variables for paths
    chroot = args.work + "/chroot_native"
    img_path = "/home/pmos/rootfs/" + args.device + ".img"
    img_path_outside = chroot + img_path

    # Umount and delete existing image
    if os.path.exists(img_path_outside):
        pmb.helpers.mount.umount_all(args, chroot + "/mnt")
        pmb.install.losetup.umount(args, img_path)
        pmb.chroot.root(args, ["rm", img_path])
        if os.path.exists(img_path_outside):
            raise RuntimeError("Failed to remove old image file: " +
                               img_path_outside)

    # Convert to MB and ask for confirmation
    mb = str(round(size / 1024 / 1024)) + "M"
    logging.info("(native) create " + args.device + ".img (" + mb + ")")
    logging.info("WARNING: Make sure, that your target device's partition"
                 " table has allocated at least " + mb + " as system"
                 " partition!")
    if not pmb.helpers.cli.confirm(args, default=True):
        raise RuntimeError("Aborted.")

    # Create empty image file
    pmb.chroot.user(args, ["mkdir", "-p", "/home/pmos/rootfs"])
    pmb.chroot.root(args, ["truncate", "-s", mb, img_path])

    # Mount to /dev/install
    logging.info("(native) mount /dev/install (" + args.device + ".img)")
    pmb.install.losetup.mount(args, img_path)
    device = pmb.install.losetup.device_by_back_file(args, img_path)
    pmb.helpers.mount.bind_blockdevice(args, device, args.work +
                                       "/chroot_native/dev/install")


def create(args, size):
    """
    Create /dev/install (the "install blockdevice").

    :param size: of the whole image in bytes
    """
    pmb.helpers.mount.umount_all(
        args, args.work + "/chroot_native/dev/install")
    if args.sdcard:
        mount_sdcard(args)
    else:
        create_and_mount_image(args, size)
