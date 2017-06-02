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
import pmb.helpers.mount
import pmb.install.losetup
import pmb.helpers.cli
import pmb.config
import fnmatch


def sdcard_validate_path(args):
    for pattern in pmb.config.install_valid_sdcard_devices:
        if fnmatch.fnmatch(args.sdcard, pattern):
            return True
    return False


def mount_sdcard(args):
    # Sanity checks
    if args.deviceinfo["external_disk_install"] != "true":
        raise RuntimeError("According to the deviceinfo, this device does"
                           " not support a sdcard installation.")
    if not os.path.exists(args.sdcard):
        raise RuntimeError("The sdcard device does not exist: " +
                           args.sdcard)
    if not sdcard_validate_path(args):
        raise RuntimeError("The sdcard path does not look valid. We will"
                           " not attempt to format this!")
    if pmb.helpers.cli.ask(args, "EVERYTHING ON " + args.sdcard + " WILL BE"
                           " ERASED! CONTINUE?") != "y":
        raise RuntimeError("Aborted.")

    logging.info("(native) mount /dev/install (host: " + args.sdcard + ")")
    pmb.helpers.mount.bind_blockdevice(args, args.sdcard,
                                       args.work + "/chroot_native/dev/install")


def create_and_mount_image(args):
    # Short variables for paths
    chroot = args.work + "/chroot_native"
    img_path = "/home/user/rootfs/" + args.device + ".img"
    img_path_outside = chroot + img_path

    # Umount and delete existing image
    if os.path.exists(img_path_outside):
        pmb.helpers.mount.umount_all(args, chroot + "/mnt")
        pmb.install.losetup.umount(args, img_path)
        pmb.chroot.root(args, ["rm", img_path])
        if os.path.exists(img_path_outside):
            raise RuntimeError("Failed to remove old image file: " +
                               img_path_outside)

    # Create empty image file
    size = pmb.config.install_size_image
    logging.info("(native) create " + args.device + ".img (" + size + ")")
    logging.info("WARNING: Make sure, that your target device's partition"
                 " table has allocated at least " + size + " as system partition!")
    if pmb.helpers.cli.ask(args) != "y":
        raise RuntimeError("Aborted.")

    pmb.chroot.user(args, ["mkdir", "-p", "/home/user/rootfs"])
    pmb.chroot.root(args, ["fallocate", "-l", size, img_path], check=False)
    if not os.path.exists(img_path_outside):
        logging.debug("WARNING: fallocate failed, falling back to truncate."
                      " More info: https://github.com/postmarketOS/pmbootstrap/issues/28")
        pmb.chroot.apk.install(args, ["coreutils"])
        pmb.chroot.root(args, ["truncate", "-s", size, img_path])

    # Mount to /dev/install
    logging.info("(native) mount /dev/install (" + args.device + ".img)")
    pmb.install.losetup.mount(args, img_path)
    device = pmb.install.losetup.device_by_back_file(args, img_path)
    pmb.helpers.mount.bind_blockdevice(args, device, args.work +
                                       "/chroot_native/dev/install")


def create(args):
    """
    Create /dev/install (the "install blockdevice").
    """
    pmb.helpers.mount.umount_all(
        args, args.work + "/chroot_native/dev/install")
    if args.sdcard:
        mount_sdcard(args)
    else:
        create_and_mount_image(args)
