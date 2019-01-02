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
import pmb.config
import pmb.chroot.apk
import pmb.helpers.mount


def init(args):
    # Validate method
    if hasattr(args, 'flash_method'):
        method = args.flash_method or args.deviceinfo["flash_method"]
    else:
        method = args.deviceinfo["flash_method"]

    if method not in pmb.config.flashers:
        raise RuntimeError("Flash method " + method + " is not supported by the"
                           " current configuration. However, adding a new flash method is "
                           " not that hard, when the flashing application already exists.\n"
                           "Make sure, it is packaged for Alpine Linux, or package it "
                           " yourself, and then add it to pmb/config/__init__.py.")
    cfg = pmb.config.flashers[method]

    # Install depends
    pmb.chroot.apk.install(args, cfg["depends"])

    # Mount folders from host system
    for folder in pmb.config.flash_mount_bind:
        pmb.helpers.mount.bind(args, folder, args.work +
                               "/chroot_native" + folder)

    # Mount device chroot inside native chroot (required for kernel/ramdisk)
    mountpoint = "/mnt/rootfs_" + args.device
    pmb.helpers.mount.bind(args, args.work + "/chroot_rootfs_" + args.device,
                           args.work + "/chroot_native" + mountpoint)
