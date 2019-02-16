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
import pmb.flasher
import pmb.chroot.initfs


def check_partition_blacklist(args, key, value):
    if not key.startswith("$PARTITION_"):
        return

    name = args.deviceinfo["name"]
    if value in args.deviceinfo["partition_blacklist"].split(","):
        raise RuntimeError("'" + value + "'" + " partition is blacklisted " +
                           "from being flashed! See the " + name + " device " +
                           "wiki page for more information.")


def run(args, action, flavor=None):
    pmb.flasher.init(args)

    # Verify action
    method = args.flash_method or args.deviceinfo["flash_method"]
    cfg = pmb.config.flashers[method]
    if action not in cfg["actions"]:
        raise RuntimeError("action " + action + " is not"
                           " configured for method " + method + "!"
                           " You can use the '--method' option to specify a"
                           " different flash method. See also:"
                           " <https://wiki.postmarketos.org/wiki/"
                           "Deviceinfo_flash_methods>")

    # Variable setup
    vars = pmb.flasher.variables(args, flavor, method)

    # Run the commands of each action
    for command in cfg["actions"][action]:
        # Variable replacement
        for key, value in vars.items():
            for i in range(len(command)):
                if key in command[i]:
                    if not value and key not in ["$KERNEL_CMDLINE", "$VENDOR_ID"]:
                        raise RuntimeError("Variable " + key + " found in"
                                           " action " + action + " for method " + method + ","
                                           " but the value for this variable is None! Is that"
                                           " missing in your deviceinfo?")
                    check_partition_blacklist(args, key, value)
                    command[i] = command[i].replace(key, value)

        # Run the action
        pmb.chroot.root(args, command, output="interactive")
