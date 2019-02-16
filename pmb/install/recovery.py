"""
Copyright 2019 Attila Szollosi

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
import pmb.flasher
import pmb.helpers.frontend


def create_zip(args, suffix):
    """
    Create android recovery compatible installer zip.
    """
    zip_root = "/var/lib/postmarketos-android-recovery-installer/"
    rootfs = "/mnt/rootfs_" + args.device
    flavor = pmb.helpers.frontend._parse_flavor(args)
    method = args.deviceinfo["flash_method"]
    vars = pmb.flasher.variables(args, flavor, method)

    # Install recovery installer package in buildroot
    pmb.chroot.apk.install(args,
                           ["postmarketos-android-recovery-installer"],
                           suffix)

    logging.info("(" + suffix + ") create recovery zip")

    for key in vars:
        pmb.flasher.check_partition_blacklist(args, key, vars[key])

    # Create config file for the recovery installer
    options = {
        "DEVICE": args.device,
        "FLAVOR": flavor,
        "FLASH_KERNEL": args.recovery_flash_kernel,
        "ISOREC": method == "heimdall-isorec",
        "KERNEL_PARTLABEL": vars["$PARTITION_KERNEL"],
        "INITFS_PARTLABEL": vars["$PARTITION_INITFS"],
        "SYSTEM_PARTLABEL": vars["$PARTITION_SYSTEM"],
        "INSTALL_PARTITION": args.recovery_install_partition,
        "CIPHER": args.cipher,
        "FDE": args.full_disk_encryption,
    }

    # Write to a temporary file
    config_temp = args.work + "/chroot_" + suffix + "/tmp/install_options"
    with open(config_temp, "w") as handle:
        for key, value in options.items():
            if isinstance(value, bool):
                value = str(value).lower()
            handle.write(key + "='" + value + "'\n")

    commands = [
        # Move config file from /tmp/ to zip root
        ["mv", "/tmp/install_options", "chroot/install_options"],
        # Create tar archive of the rootfs
        ["tar", "-pcf", "rootfs.tar", "--exclude", "./home", "-C", rootfs,
         "."],
        # Append packages keys
        ["tar", "-prf", "rootfs.tar", "-C", "/", "./etc/apk/keys"],
        # Compress with -1 for speed improvement
        ["gzip", "-f1", "rootfs.tar"],
        ["build-recovery-zip", args.device]]
    for command in commands:
        pmb.chroot.root(args, command, suffix, zip_root)
