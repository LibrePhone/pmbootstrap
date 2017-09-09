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
import pmb.flasher
import pmb.chroot.initfs


def run(args, action, flavor=None):
    pmb.flasher.init(args)

    # Verify action
    method = args.flash_method or args.deviceinfo["flash_methods"]
    cfg = pmb.config.flashers[method]
    if action not in cfg["actions"]:
        raise RuntimeError("action " + action + " is not"
                           " configured for method " + method + "!")

    _cmdline = args.deviceinfo["kernel_cmdline"]
    if "cmdline" in args and args.cmdline:
        _cmdline = args.cmdline

    # Variable setup
    vars = {
        "$BOOT": "/mnt/rootfs_" + args.device + "/boot",
        "$FLAVOR": flavor if flavor is not None else "",
        "$IMAGE": "/home/user/rootfs/" + args.device + ".img",
        "$KERNEL_CMDLINE": _cmdline,
        "$PARTITION_KERNEL": args.deviceinfo["flash_heimdall_partition_kernel"] or "KERNEL",
        "$PARTITION_INITFS": args.deviceinfo["flash_heimdall_partition_initfs"] or "RECOVERY",
        "$PARTITION_SYSTEM": args.deviceinfo["flash_heimdall_partition_system"] or "SYSTEM",
        "$RECOVERY_ZIP": "/mnt/buildroot_" + args.deviceinfo["arch"] +
                         "/var/lib/postmarketos-android-recovery-installer"
                         "/pmos-" + args.device + ".zip",
    }

    # Run the commands of each action
    for command in cfg["actions"][action]:
        # Variable replacement
        for key, value in vars.items():
            for i in range(len(command)):
                if key in command[i]:
                    if not value and key != "$KERNEL_CMDLINE":
                        raise RuntimeError("Variable " + key + " found in"
                                           " action " + action + " for method " + method + ","
                                           " but the value for this variable is None! Is that"
                                           " missing in your deviceinfo?")
                    command[i] = command[i].replace(key, value)

        # Run the action
        pmb.chroot.root(args, command, log=False)
