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
import glob
import os

import pmb.chroot
import pmb.chroot.distccd
import pmb.helpers.mount
import pmb.install.losetup
import pmb.parse.arch


def shutdown_cryptsetup_device(args, name):
    """
    :param name: cryptsetup device name, usually "pm_crypt" in pmbootstrap
    """
    if not os.path.exists(args.work + "/chroot_native/dev/mapper/" + name):
        return
    pmb.chroot.apk.install(args, ["cryptsetup"])
    status = pmb.chroot.root(args, ["cryptsetup", "status", name], check=False,
                             return_stdout=True)
    if not status:
        logging.warning("WARNING: Failed to run cryptsetup to get the status"
                        " for " + name + ", assuming it is not mounted"
                        " (shutdown fails later if it is)!")
        return

    if status.startswith("/dev/mapper/" + name + " is active."):
        pmb.chroot.root(args, ["cryptsetup", "luksClose", name])
    elif status.startswith("/dev/mapper/" + name + " is inactive."):
        # When "cryptsetup status" fails, the device is not mounted and we
        # have a left over file (#83)
        pmb.chroot.root(args, ["rm", "/dev/mapper/" + name])
    else:
        raise RuntimeError("Failed to parse 'cryptsetup status' output!")


def shutdown(args, only_install_related=False):
    pmb.chroot.distccd.stop(args)

    # Umount installation-related paths (order is important!)
    pmb.helpers.mount.umount_all(args, args.work +
                                 "/chroot_native/mnt/install")
    shutdown_cryptsetup_device(args, "pm_crypt")

    # Umount all losetup mounted images
    chroot = args.work + "/chroot_native"
    if pmb.helpers.mount.ismount(chroot + "/dev/loop-control"):
        pattern = chroot + "/home/user/rootfs/*.img"
        for path_outside in glob.glob(pattern):
            path = path_outside[len(chroot):]
            pmb.install.losetup.umount(args, path)

    if not only_install_related:
        # Clean up the rest
        pmb.helpers.mount.umount_all(args, args.work)
        arch = args.deviceinfo["arch"]
        if pmb.parse.arch.cpu_emulation_required(args, arch):
            pmb.chroot.binfmt.unregister(args, arch)
        logging.info("Shutdown complete")
