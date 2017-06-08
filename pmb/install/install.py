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

import pmb.chroot
import pmb.chroot.apk
import pmb.config
import pmb.helpers.run
import pmb.install.blockdevice
import pmb.install


def copy_files(args):
    # Mount the device rootfs
    logging.info("(native) copy rootfs_" + args.device + " to" +
                 " /mnt/install/")
    mountpoint = "/mnt/rootfs_" + args.device
    pmb.helpers.mount.bind(args, args.work + "/chroot_rootfs_" + args.device,
                           args.work + "/chroot_native" + mountpoint)

    # Get all folders inside the device rootfs
    folders = []
    for path in glob.glob(args.work + "/chroot_native" + mountpoint + "/*"):
        folders += [os.path.basename(path)]

    # Run the copy command
    pmb.chroot.root(args, ["cp", "-a"] + folders + ["/mnt/install/"],
                    working_dir=mountpoint)

# copy over keys and delete unneded mount folders


def fix_mount_folders(args):
    # copy over keys
    rootfs = args.work + "/chroot_native/mnt/install/"
    for key in glob.glob(args.work + "/config_apk_keys/*.pub"):
        pmb.helpers.run.root(args, ["cp", key, rootfs + "/etc/apk/keys/"])

    # delete everything (-> empty mount folders) in /home/user
    pmb.helpers.run.root(args, ["rm", "-r", rootfs + "/home/user"])
    pmb.helpers.run.root(args, ["mkdir", rootfs + "/home/user"])
    pmb.helpers.run.root(args, ["chown", pmb.config.chroot_uid_user,
                                rootfs + "/home/user"])


def set_user_password(args):
    """
    Loop until the passwords for user and root have been changed successfully.
    """
    suffix = "rootfs_" + args.device
    while True:
        try:
            pmb.chroot.root(args, ["passwd", "user"], suffix, log=False)
            break
        except RuntimeError:
            logging.info("WARNING: Failed to set the password. Try it"
                         " one more time.")
            pass


def install(args, show_flash_msg=True):
    # Install required programs in native chroot
    logging.info("*** (1/5) PREPARE NATIVE CHROOT ***")
    pmb.chroot.apk.install(args, pmb.config.install_native_packages,
                           build=False)

    # List all packages to be installed (including the ones specified by --add)
    # and upgrade the installed packages/apkindexes
    logging.info("*** (2/5) CREATE DEVICE ROOTFS (" + args.device + ") ***")
    install_packages = (pmb.config.install_device_packages + ["device-" + args.device])
    suffix = "rootfs_" + args.device
    pmb.chroot.apk.upgrade(args, suffix)

    # Explicitly call build on the install packages, to re-build them or any
    # dependency, in case the version increased
    if args.add:
        install_packages += args.add.split(",")
    for pkgname in install_packages:
        pmb.build.package(args, pkgname, args.deviceinfo["arch"])

    # Install all packages to device rootfs chroot
    pmb.chroot.apk.install(args, install_packages, suffix)
    set_user_password(args)

    # Partition and fill image/sdcard
    logging.info("*** (3/5) PREPARE INSTALL BLOCKDEVICE ***")
    pmb.chroot.shutdown(args, True)
    pmb.install.blockdevice.create(args)
    pmb.install.partition(args)
    pmb.install.format(args)

    # Just copy all the files
    logging.info("*** (4/5) FILL INSTALL BLOCKDEVICE ***")
    copy_files(args)
    fix_mount_folders(args)
    pmb.chroot.shutdown(args, True)

    # Flash to target device
    logging.info("*** (5/5) FLASHING TO DEVICE ***")
    if show_flash_msg:
        logging.info("Run the following to flash your installation to the"
                     " target device:")
        logging.info("* pmbootstrap flasher flash_kernel")
        if not args.sdcard:
            logging.info("* pmbootstrap flasher flash_system")
