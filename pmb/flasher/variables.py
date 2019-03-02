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


def variables(args, flavor, method):
    _cmdline = args.deviceinfo["kernel_cmdline"]
    if "cmdline" in args and args.cmdline:
        _cmdline = args.cmdline

    if method == "fastboot":
        _partition_kernel = args.deviceinfo["flash_fastboot_partition_kernel"] or "boot"
        _partition_system = args.deviceinfo["flash_fastboot_partition_system"] or "system"
    else:
        _partition_kernel = args.deviceinfo["flash_heimdall_partition_kernel"] or "KERNEL"
        _partition_system = args.deviceinfo["flash_heimdall_partition_system"] or "SYSTEM"

    if "partition" in args and args.partition:
        # Only one of two operations is done at same time so it doesn't matter sharing the arg
        _partition_kernel = args.partition
        _partition_system = args.partition

    vars = {
        "$BOOT": "/mnt/rootfs_" + args.device + "/boot",
        "$FLAVOR": flavor if flavor is not None else "",
        "$IMAGE": "/home/pmos/rootfs/" + args.device + ".img",
        "$VENDOR_ID": args.deviceinfo["flash_fastboot_vendor_id"],
        "$KERNEL_CMDLINE": _cmdline,
        "$PARTITION_KERNEL": _partition_kernel,
        "$PARTITION_INITFS": args.deviceinfo["flash_heimdall_partition_initfs"] or "RECOVERY",
        "$PARTITION_SYSTEM": _partition_system,
        "$RECOVERY_ZIP": "/mnt/buildroot_" + args.deviceinfo["arch"] +
                         "/var/lib/postmarketos-android-recovery-installer"
                         "/pmos-" + args.device + ".zip",
        "$UUU_SCRIPT": "/mnt/rootfs_" + args.deviceinfo["codename"] +
                       "/usr/share/uuu/flash_script.lst"
    }

    return vars
