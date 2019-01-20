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
import os
import logging
import pmb.chroot


def format_and_mount_boot(args):
    mountpoint = "/mnt/install/boot"
    device = "/dev/installp1"
    filesystem = args.deviceinfo["boot_filesystem"] or "ext2"
    logging.info("(native) format " + device + " (boot, " + filesystem + "), mount to " +
                 mountpoint)
    if filesystem == "fat16":
        pmb.chroot.root(args, ["mkfs.fat", "-F", "16", "-n", "pmOS_boot", device])
    elif filesystem == "ext2":
        pmb.chroot.root(args, ["mkfs.ext2", "-F", "-q", "-L", "pmOS_boot", device])
    else:
        raise RuntimeError("Filesystem " + filesystem + " is not supported!")
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
                               "--iter-time", args.iter_time],
                        output="interactive")
        pmb.chroot.root(args, ["cryptsetup", "luksOpen", device,
                               "pm_crypt"], output="interactive")
        if not os.path.exists(args.work + "/chroot_native" + mountpoint):
            raise RuntimeError("Failed to open cryptdevice!")


def format_and_mount_pm_crypt(args):
    # Block device
    if args.full_disk_encryption:
        device = "/dev/mapper/pm_crypt"
    else:
        device = "/dev/installp2"

    # Format
    if not args.rsync:
        logging.info("(native) format " + device)
        # Some downstream kernels don't support metadata_csum (#1364).
        # When changing the options of mkfs.ext4, also change them in the
        # recovery zip code (see 'grep -r mkfs\.ext4')!
        pmb.chroot.root(args, ["mkfs.ext4", "-O", "^metadata_csum", "-F",
                               "-q", "-L", "pmOS_root", "-N", "100000",
                               device])

    # Mount
    mountpoint = "/mnt/install"
    logging.info("(native) mount " + device + " to " + mountpoint)
    pmb.chroot.root(args, ["mkdir", "-p", mountpoint])
    pmb.chroot.root(args, ["mount", device, mountpoint])


def format(args):
    format_and_mount_root(args)
    format_and_mount_pm_crypt(args)
    format_and_mount_boot(args)
