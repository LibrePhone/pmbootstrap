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

import pmb.install.losetup
import pmb.helpers.mount
import pmb.chroot
import pmb.chroot.distccd


def shutdown(args, only_install_related=False):
    pmb.chroot.distccd.stop(args)

    # Umount installation-related paths (order is important!)
    pmb.helpers.mount.umount_all(args, args.work +
                                 "/chroot_native/mnt/install/boot")
    pmb.helpers.mount.umount_all(args, args.work +
                                 "/chroot_native/mnt/install")
    if os.path.exists(args.work + "/chroot_native/dev/mapper/pm_crypt"):
        pmb.chroot.root(args, ["cryptsetup", "luksClose", "pm_crypt"])

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
        pmb.helpers.mount.umount_all(args, args.work)
        pmb.chroot.binfmt.unregister(args, args.deviceinfo["arch"])
        logging.info("Shutdown complete")
