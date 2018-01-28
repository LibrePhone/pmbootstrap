"""
Copyright 2018 Oliver Smith

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
import pmb.helpers.run
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
            ret = os.path.realpath(ret)

            # Work must not be inside the pmbootstrap path
            if ret == pmb.config.pmb_src or ret.startswith(pmb.config.pmb_src +
                                                           "/"):
                logging.fatal("ERROR: The work path must not be inside the"
                              " pmbootstrap path. Please specify another"
                              " location.")
                continue

            # Create the folder with a version file
            if not os.path.exists(ret):
                os.makedirs(ret, 0o700, True)
                with open(ret + "/version", "w") as handle:
                    handle.write(pmb.config.work_version + "\n")

            # Make sure, that we can write into it
            os.makedirs(ret + "/cache_http", 0o700, True)
            return ret
        except OSError:
            logging.fatal("ERROR: Could not create this folder, or write"
                          " inside it! Please try again.")


def ask_for_ui(args):
    ui_list = pmb.helpers.ui.list(args)
    logging.info("Available user interfaces (" +
                 str(len(ui_list) - 1) + "): ")
    for ui in ui_list:
        logging.info("* " + ui[0] + ": " + ui[1])
    while True:
        ret = pmb.helpers.cli.ask(args, "User interface", None, args.ui, True)
        if ret in dict(ui_list).keys():
            return ret
        logging.fatal("ERROR: Invalid user interface specified, please type in"
                      " one from the list above.")


def ask_for_keymaps(args, device):
    info = pmb.parse.deviceinfo(args, device)
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


def ask_for_timezone(args):
    localtimes = ["/etc/zoneinfo/localtime", "/etc/localtime"]
    zoneinfo_path = "/usr/share/zoneinfo/"
    for localtime in localtimes:
        if not os.path.exists(localtime):
            continue
        tz = ""
        if os.path.exists(localtime):
            tzpath = os.path.realpath(localtime)
            tzpath = tzpath.rstrip()
            if os.path.exists(tzpath):
                try:
                    _, tz = tzpath.split(zoneinfo_path)
                except:
                    pass
        if tz:
            logging.info("Your host timezone: " + tz)
            if pmb.helpers.cli.confirm(args, "Use this timezone instead of GMT?",
                                       default="y"):
                return tz
    logging.info("WARNING: Unable to determine timezone configuration on host,"
                 " using GMT.")
    return "GMT"


def ask_for_device(args):
    devices = sorted(pmb.helpers.devices.list(args))
    logging.info("Target device (either an existing one, or a new one for"
                 " porting).")
    logging.info("Available (" + str(len(devices)) + "): " +
                 ", ".join(devices))
    while True:
        device = pmb.helpers.cli.ask(args, "Device", None, args.device, False,
                                     "[a-z0-9]+-[a-z0-9]+")
        device_exists = os.path.exists(args.aports + "/device/device-" +
                                       device + "/deviceinfo")
        if not device_exists:
            logging.info("You are about to do a new device port for '" +
                         device + "'.")
            if not pmb.helpers.cli.confirm(args, default=True):
                continue

            pmb.aportgen.generate(args, "device-" + device)
            pmb.aportgen.generate(args, "linux-" + device)
        break

    return (device, device_exists)


def ask_for_qemu_native_mesa_driver(args, device, arch_native):
    # Native Qemu device selected? (e.g. qemu-amd64 on x86_64)
    if not pmb.parse.arch.qemu_check_device(device, arch_native):
        return None

    drivers = pmb.config.qemu_native_mesa_drivers
    logging.info("Which mesa driver do you prefer for your native Qemu device?"
                 " Only select something other than the default if you are"
                 " having graphical problems (such as glitches).")
    while True:
        ret = pmb.helpers.cli.ask(args, "Mesa driver", drivers,
                                  args.qemu_native_mesa_driver)
        if ret in drivers:
            return ret
        logging.fatal("ERROR: Please specify a driver from the list. To change"
                      " it, see qemu_native_mesa_drivers in"
                      " pmb/config/__init__.py.")


def ask_for_build_options(args, cfg):
    # Allow to skip build options
    logging.info("Build options: Parallel jobs: " + args.jobs +
                 ", ccache per arch: " + args.ccache_size)

    if not pmb.helpers.cli.confirm(args, "Change them?",
                                   default=False):
        return

    # Parallel job count
    logging.info("How many jobs should run parallel on this machine, when"
                 " compiling?")
    answer = pmb.helpers.cli.ask(args, "Jobs", None, args.jobs,
                                 validation_regex="[1-9][0-9]*")
    cfg["pmbootstrap"]["jobs"] = answer

    # Ccache size
    logging.info("We use ccache to speed up building the same code multiple"
                 " times. How much space should the ccache folder take up per"
                 " architecture? After init is through, you can check the current"
                 " usage with 'pmbootstrap stats'. Answer with 0 for infinite.")
    regex = "0|[0-9]+(k|M|G|T|Ki|Mi|Gi|Ti)"
    answer = pmb.helpers.cli.ask(args, "Ccache size", None, args.ccache_size,
                                 lowercase_answer=False, validation_regex=regex)
    cfg["pmbootstrap"]["ccache_size"] = answer


def frontend(args):
    cfg = pmb.config.load(args)

    # Work folder (needs to be first, so boot.img analyze works: #1066)
    cfg["pmbootstrap"]["work"] = args.work = ask_for_work_path(args)

    # Device
    device, device_exists = ask_for_device(args)
    cfg["pmbootstrap"]["device"] = device

    # Qemu mesa driver
    if cfg["pmbootstrap"]["device"].startswith("qemu-"):
        driver = ask_for_qemu_native_mesa_driver(args, device, args.arch_native)
        if driver:
            cfg["pmbootstrap"]["qemu_native_mesa_driver"] = driver

    # Device keymap
    if device_exists:
        cfg["pmbootstrap"]["keymap"] = ask_for_keymaps(args, device)

    # Username
    cfg["pmbootstrap"]["user"] = pmb.helpers.cli.ask(args, "Username", None,
                                                     args.user, False,
                                                     "[a-z_][a-z0-9_-]*")
    # UI and various build options
    cfg["pmbootstrap"]["ui"] = ask_for_ui(args)
    ask_for_build_options(args, cfg)

    # Extra packages to be installed to rootfs
    logging.info("Additional packages that will be installed to rootfs."
                 " Specify them in a comma separated list (e.g.: vim,file)"
                 " or \"none\"")
    cfg["pmbootstrap"]["extra_packages"] = pmb.helpers.cli.ask(args, "Extra packages",
                                                               None, args.extra_packages,
                                                               validation_regex="^(|[-.+\w\s]+(?:,[-.+\w\s]*)*)$")

    # Configure timezone info
    cfg["pmbootstrap"]["timezone"] = ask_for_timezone(args)

    # Save config
    pmb.config.save(args, cfg)

    # Zap existing chroots
    setattr(args, "work", cfg["pmbootstrap"]["work"])
    if (device_exists and
            len(glob.glob(args.work + "/chroot_*")) and
            pmb.helpers.cli.confirm(args, "Zap existing chroots to apply configuration?", default=True)):
        setattr(args, "deviceinfo", pmb.parse.deviceinfo(args, device=device))

        # Do not zap any existing packages or cache_http directories
        pmb.chroot.zap(args, confirm=False)

    logging.info(
        "WARNING: The applications in the chroots do not get updated automatically.")
    logging.info("Run 'pmbootstrap zap' to delete all chroots once a day before"
                 " working with pmbootstrap!")
    logging.info("It only takes a few seconds, and all packages are cached.")

    logging.info("Done!")
