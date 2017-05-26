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
import pmb.chroot


def format_and_mount_boot(args):
    mountpoint = "/mnt/install/boot"
    logging.info("(native) format /dev/installp1 (boot, ext2), mount to " +
                 mountpoint)
    pmb.chroot.root(args, ["mkfs.ext2", "-F", "-q", "/dev/installp1"])
    pmb.chroot.root(args, ["mkdir", "-p", mountpoint])
    pmb.chroot.root(args, ["mount", "/dev/installp1", mountpoint])


def format_and_mount_root(args):
    mountpoint = "/dev/mapper/pm_crypt"
    logging.info("(native) format /dev/installp2 (root, luks), mount to " +
                 mountpoint)
    pmb.chroot.root(args, ["cryptsetup", "luksFormat", "--use-urandom",
                           "--cipher", args.cipher, "-q", "/dev/installp2"], log=False)
    pmb.chroot.root(args, ["cryptsetup", "luksOpen", "/dev/installp2",
                           "pm_crypt"], log=False)
    if not os.path.exists(args.work + "/chroot_native" + mountpoint):
        raise RuntimeError("Failed to open cryptdevice!")


def format_and_mount_pm_crypt(args):
    cryptdevice = "/dev/mapper/pm_crypt"
    mountpoint = "/mnt/install"
    logging.info("(native) format " + cryptdevice + " (ext4), mount to " +
                 mountpoint)
    pmb.chroot.root(args, ["mkfs.ext4", "-F", "-q", cryptdevice])
    pmb.chroot.root(args, ["mkdir", "-p", mountpoint])
    pmb.chroot.root(args, ["mount", cryptdevice, mountpoint])


def format(args):
    format_and_mount_root(args)
    format_and_mount_pm_crypt(args)
    format_and_mount_boot(args)
