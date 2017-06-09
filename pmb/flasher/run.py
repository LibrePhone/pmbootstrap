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


def run(args, action, kernel=None, ramdisk=None, image=None):
    pmb.flasher.init(args)

    # Verify action
    method = args.deviceinfo["flash_methods"]
    cfg = pmb.config.flashers[method]
    if action not in cfg["actions"]:
        raise RuntimeError("action " + action + " is not"
                           " configured for method " + method + "!")

    # Variable setup
    vars = {
        "$KERNEL": kernel,
        "$RAMDISK": ramdisk,
        "$IMAGE": image,
        "$OFFSET_BASE": args.deviceinfo["flash_offset_base"],
        "$OFFSET_KERNEL": args.deviceinfo["flash_offset_kernel"],
        "$OFFSET_RAMDISK": args.deviceinfo["flash_offset_ramdisk"],
        "$OFFSET_SECOND": args.deviceinfo["flash_offset_second"],
        "$OFFSET_TAGS": args.deviceinfo["flash_offset_tags"],
        "$PAGE_SIZE": args.deviceinfo["flash_pagesize"],
    }

    # Run the commands of each action
    for command in cfg["actions"][action]:
        # Variable replacement
        for key, value in vars.items():
            for i in range(len(command)):
                if key in command[i]:
                    if not value:
                        raise RuntimeError("Variable " + key + " found in"
                                           " action " + action + " for method " + method + ","
                                           " but the value for this variable is None!")
                    command[i] = command[i].replace(key, value)

        # Run the action
        pmb.chroot.root(args, command, log=False)
