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
    device = "/dev/installp1"
    logging.info("(native) format " + device + " (boot, ext2), mount to " +
                 mountpoint)
    pmb.chroot.root(args, ["mkfs.ext2", "-F", "-q", "-L", "pmOS_boot", device])
    pmb.chroot.root(args, ["mkdir", "-p", mountpoint])
    pmb.chroot.root(args, ["mount", device, mountpoint])


def format_and_mount_root(args):
    mountpoint = "/dev/mapper/pm_crypt"
    device = "/dev/installp2"
    if args.full_disk_encryption:
        logging.info("(native) format " + device + " (root, luks), mount to " +
                     mountpoint)
        logging.info(
            " *** TYPE IN THE FULL DISK ENCRYPTION PASSWORD (TWICE!) ***")
        pmb.chroot.root(args, ["cryptsetup", "luksFormat", "--use-urandom",
                               "--cipher", args.cipher, "-q", device,
                               "--iter-time", args.iter_time], log=False)
        pmb.chroot.root(args, ["cryptsetup", "luksOpen", device,
                               "pm_crypt"], log=False)
        if not os.path.exists(args.work + "/chroot_native" + mountpoint):
            raise RuntimeError("Failed to open cryptdevice!")


def format_and_mount_pm_crypt(args):
    if args.full_disk_encryption:
        device = "/dev/mapper/pm_crypt"
    else:
        device = "/dev/installp2"
    mountpoint = "/mnt/install"
    logging.info("(native) format " + device + " (ext4), mount to " +
                 mountpoint)
    pmb.chroot.root(args, ["mkfs.ext4", "-F", "-q", "-L", "pmOS_root", device])
    pmb.chroot.root(args, ["mkdir", "-p", mountpoint])
    pmb.chroot.root(args, ["mount", device, mountpoint])


def format(args):
    format_and_mount_root(args)
    format_and_mount_pm_crypt(args)
    format_and_mount_boot(args)
