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

import pmb.config
import pmb.flasher
import pmb.install
import pmb.chroot.apk
import pmb.chroot.initfs
import pmb.chroot.other
import pmb.helpers.frontend
import pmb.parse.kconfig


def kernel(args):
    # Rebuild the initramfs, just to make sure (see #69)
    flavor = pmb.helpers.frontend._parse_flavor(args)
    pmb.chroot.initfs.build(args, flavor, "rootfs_" + args.device)

    # Check kernel config
    pmb.parse.kconfig.check(args, flavor)

    # Generate the paths and run the flasher
    if args.action_flasher == "boot":
        logging.info("(native) boot " + flavor + " kernel")
        pmb.flasher.run(args, "boot", flavor)
    else:
        logging.info("(native) flash kernel " + flavor)
        pmb.flasher.run(args, "flash_kernel", flavor)
    logging.info("You will get an IP automatically assigned to your "
                 "USB interface shortly.")
    logging.info("Then you can connect to your device using ssh after pmOS has booted:")
    logging.info("ssh {}@{}".format(args.user, pmb.config.default_ip))
    logging.info("NOTE: If you enabled full disk encryption, you should make sure that"
                 " osk-sdl has been properly configured for your device")


def list_flavors(args):
    suffix = "rootfs_" + args.device
    logging.info("(" + suffix + ") installed kernel flavors:")
    for flavor in pmb.chroot.other.kernel_flavors_installed(args, suffix):
        logging.info("* " + flavor)


def rootfs(args):
    # Generate rootfs, install flasher
    img_path = "/home/pmos/rootfs/" + args.device + ".img"
    if not os.path.exists(args.work + "/chroot_native" + img_path):
        raise RuntimeError("The rootfs has not been generated yet, please run"
                           " 'pmbootstrap install' first.")

    # Do not flash if using fastboot & image is too large
    method = args.flash_method or args.deviceinfo["flash_method"]
    if method == "fastboot" and args.deviceinfo["flash_fastboot_max_size"]:
        img_size = os.path.getsize(args.work + "/chroot_native" + img_path) / 1024**2
        max_size = int(args.deviceinfo["flash_fastboot_max_size"])
        if img_size > max_size:
            raise RuntimeError("The rootfs is too large for fastboot to"
                               " flash.")

    # Run the flasher
    logging.info("(native) flash rootfs image")
    pmb.flasher.run(args, "flash_rootfs")


def list_devices(args):
    pmb.flasher.run(args, "list_devices")


def sideload(args):
    method = args.flash_method or args.deviceinfo["flash_method"]
    cfg = pmb.config.flashers[method]

    # Install depends
    pmb.chroot.apk.install(args, cfg["depends"])

    # Mount the buildroot
    suffix = "buildroot_" + args.deviceinfo["arch"]
    mountpoint = "/mnt/" + suffix
    pmb.helpers.mount.bind(args, args.work + "/chroot_" + suffix,
                           args.work + "/chroot_native/" + mountpoint)

    # Missing recovery zip error
    zip_path = ("/var/lib/postmarketos-android-recovery-installer/pmos-" +
                args.device + ".zip")
    if not os.path.exists(args.work + "/chroot_native" + mountpoint +
                          zip_path):
        raise RuntimeError("The recovery zip has not been generated yet,"
                           " please run 'pmbootstrap install' with the"
                           " '--android-recovery-zip' parameter first!")

    pmb.flasher.run(args, "sideload")


def frontend(args):
    action = args.action_flasher
    method = args.flash_method or args.deviceinfo["flash_method"]

    # Legacy alias
    if action == "flash_system":
        action = "flash_rootfs"

    if method == "none" and action in ["boot", "flash_kernel", "flash_rootfs"]:
        logging.info("This device doesn't support any flash method.")
        return

    if action in ["boot", "flash_kernel"]:
        kernel(args)
    if action == "flash_rootfs":
        rootfs(args)
    if action == "list_flavors":
        list_flavors(args)
    if action == "list_devices":
        list_devices(args)
    if action == "sideload":
        sideload(args)
