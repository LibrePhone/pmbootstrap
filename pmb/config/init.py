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
import logging
import glob
import os

import pmb.config
import pmb.helpers.cli
import pmb.helpers.devices
import pmb.helpers.ui
import pmb.chroot.zap
import pmb.parse.deviceinfo


def ask_for_work_path(args):
    """
    Ask for the work path, until we can create it (when it does not exist) and
    write into it.
    :returns: the work path
    """
    logging.info("Location of the 'work' path. Multiple chroots"
                 " (native, device arch, device rootfs) will be created"
                 " in there.")
    while True:
        try:
            ret = os.path.expanduser(pmb.helpers.cli.ask(
                args, "Work path", None, args.work, False))
            os.makedirs(ret, 0o700, True)
            os.makedirs(ret + "/cache_http", 0o700, True)
            return ret
        except OSError:
            logging.fatal("ERROR: Could not create this folder, or write"
                          " inside it! Please try again.")


def ask_for_ui(args):
    ui_list = pmb.helpers.ui.list(args)
    logging.info("Available user interfaces (" +
                 str(len(ui_list) - 1) + "): " + ", ".join(ui_list))
    while True:
        ret = pmb.helpers.cli.ask(args, "User interface", None, args.ui, True)
        if ret in ui_list:
            return ret
        logging.fatal("ERROR: Invalid user interface specified, please type in"
                      " one from the list above.")


def ask_for_keymaps(args, device):
    info = pmb.parse.deviceinfo(args, device=device)
    if "keymaps" not in info or info["keymaps"].strip() == "":
        return ""
    options = info["keymaps"].split(' ')
    logging.info("Available keymaps for device (" + str(len(options)) +
                 "): " + ", ".join(options))
    if args.keymap is "":
        args.keymap = options[0]

    while True:
        ret = pmb.helpers.cli.ask(args, "Keymap", None, args.keymap, True)
        if ret in options:
            return ret
        logging.fatal("ERROR: Invalid keymap specified, please type in"
                      " one from the list above.")


def init(args):
    cfg = pmb.config.load(args)

    # Device
    devices = sorted(pmb.helpers.devices.list(args))
    logging.info("Target device (either an existing one, or a new one for"
                 " porting).")
    logging.info("Available (" + str(len(devices)) + "): " +
                 ", ".join(devices))
    cfg["pmbootstrap"]["device"] = pmb.helpers.cli.ask(args, "Device",
                                                       None, args.device, False, "[a-z0-9]+-[a-z0-9]+")

    device_exists = os.path.exists(args.aports + "/device/device-" + cfg["pmbootstrap"]["device"] + "/deviceinfo")

    # Device keymap
    if device_exists:
        cfg["pmbootstrap"]["keymap"] = ask_for_keymaps(args, device=cfg["pmbootstrap"]["device"])

    # UI and work folder
    cfg["pmbootstrap"]["ui"] = ask_for_ui(args)
    cfg["pmbootstrap"]["work"] = ask_for_work_path(args)

    # Parallel job count
    logging.info("How many jobs should run parallel on this machine, when"
                 " compiling?")
    cfg["pmbootstrap"]["jobs"] = pmb.helpers.cli.ask(args, "Jobs",
                                                     None, args.jobs, validation_regex="[1-9][0-9]*")

    # Timestamp based rebuilds
    logging.info("Rebuild packages, when the last modified timestamp changed,"
                 " even if the version did not change? This makes pmbootstrap"
                 " behave more like 'make'.")
    answer = pmb.helpers.cli.confirm(args, "Timestamp based rebuilds",
                                     default=args.timestamp_based_rebuild)
    cfg["pmbootstrap"]["timestamp_based_rebuild"] = str(answer)

    # Extra packages to be installed to rootfs
    logging.info("Additional packages that will be installed to rootfs."
                 " Specify them in a comma separated list (e.g.: vim,file)"
                 " or \"none\"")
    cfg["pmbootstrap"]["extra_packages"] = pmb.helpers.cli.ask(args, "Extra packages",
                                                               None, args.extra_packages,
                                                               validation_regex="^(|[-.+\w\s]+(?:,[-.+\w\s]*)*)$")

    # Do not save aports location to config file
    del cfg["pmbootstrap"]["aports"]

    # Save config
    pmb.config.save(args, cfg)

    # Zap existing chroots
    setattr(args, "work", cfg["pmbootstrap"]["work"])
    if (device_exists and
            len(glob.glob(args.work + "/chroot_*")) and
            pmb.helpers.cli.confirm(args, "Zap existing chroots to apply configuration?", default=True)):
        setattr(args, "deviceinfo", pmb.parse.deviceinfo(args, device=cfg["pmbootstrap"]["device"]))
        # Do not zap any existing packages or cache_http directories
        pmb.chroot.zap(args, confirm=False)

    logging.info(
        "WARNING: The applications in the chroots do not get updated automatically.")
    logging.info("Run 'pmbootstrap zap' to delete all chroots once a day before"
                 " working with pmbootstrap!")
    logging.info("It only takes a few seconds, and all packages are cached.")

    logging.info("Done!")
