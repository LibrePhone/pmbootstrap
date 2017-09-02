"""
Copyright 2017 Attila Szollosi

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

import pmb.chroot
import pmb.helpers.frontend


def create_zip(args, suffix):
    """
    Create android recovery compatible installer zip.
    """
    zip_root = "/var/lib/postmarketos-android-recovery-installer/"
    rootfs = "/mnt/rootfs_" + args.device
    flavor = pmb.helpers.frontend._parse_flavor(args)

    # Install recovery installer package in buildroot
    pmb.chroot.apk.install(args,
                           ["postmarketos-android-recovery-installer"],
                           suffix)

    logging.info("(" + suffix + ") create recovery zip")

    # Create config file for the recovery installer
    with open(args.work + "/chroot_" + suffix + "/tmp/install_options",
              "w") as install_options:
        install_options.write(
            "\n".join(['DEVICE="{}"'.format(args.device),
                       'FLASH_BOOTIMG="{}"'.format(
                           str(args.recovery_flash_bootimg).lower()),
                       'INSTALL_PARTITION="{}"'.format(
                           args.recovery_install_partition),
                       'CIPHER="{}"'.format(args.cipher),
                       'FDE="{}"'.format(
                           str(args.full_disk_encryption).lower())]))

    commands = [
        # Move config file from /tmp/ to zip root
        ["mv", "/tmp/install_options", "install_options"],
        # Copy boot.img to zip root
        ["cp", rootfs + "/boot/boot.img-" + flavor, "boot.img"],
        # Create tar archive of the rootfs
        ["tar", "-pczf", "rootfs.tar.gz", "--exclude", "./home/user/*",
         "-C", rootfs, "."],
        ["build-recovery-zip"]]
    for command in commands:
        pmb.chroot.root(args, command, suffix, working_dir=zip_root)
