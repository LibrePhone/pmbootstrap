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
import logging
import glob
import os

import pmb.config
import pmb.config.pmaports
import pmb.helpers.cli
import pmb.helpers.devices
import pmb.helpers.logging
import pmb.helpers.run
import pmb.helpers.ui
import pmb.chroot.zap
import pmb.parse.deviceinfo
import pmb.parse._apkbuild


def ask_for_work_path(args):
    """
    Ask for the work path, until we can create it (when it does not exist) and
    write into it.
    :returns: (path, exists)
              * path: is the full path, with expanded ~ sign
              * exists: is False when the folder did not exist before we tested
                        whether we can create it
    """
    logging.info("Location of the 'work' path. Multiple chroots"
                 " (native, device arch, device rootfs) will be created"
                 " in there.")
    while True:
        try:
            work = os.path.expanduser(pmb.helpers.cli.ask(
                args, "Work path", None, args.work, False))
            work = os.path.realpath(work)
            exists = os.path.exists(work)

            # Work must not be inside the pmbootstrap path
            if (work == pmb.config.pmb_src or
                    work.startswith(pmb.config.pmb_src + "/")):
                logging.fatal("ERROR: The work path must not be inside the"
                              " pmbootstrap path. Please specify another"
                              " location.")
                continue

            # Create the folder with a version file
            if not exists:
                os.makedirs(work, 0o700, True)
                with open(work + "/version", "w") as handle:
                    handle.write(str(pmb.config.work_version) + "\n")

            # Make sure, that we can write into it
            os.makedirs(work + "/cache_http", 0o700, True)
            return (work, exists)
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
    if args.keymap == "":
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


def ask_for_device_kernel(args, device):
    """
    Ask for the kernel that should be used with the device.

    :param device: code name, e.g. "lg-mako"
    :returns: None if the kernel is hardcoded in depends without subpackages
    :returns: kernel type ("downstream", "stable", "mainline", ...)
    """
    # Get kernels
    kernels = pmb.parse._apkbuild.kernels(args, device)
    if not kernels:
        return args.kernel

    # Get default
    default = args.kernel
    if default not in kernels:
        default = list(kernels.keys())[0]

    # Ask for kernel (extra message when downstream and upstream are available)
    logging.info("Which kernel do you want to use with your device?")
    if "downstream" in kernels:
        logging.info("Downstream kernels are typically the outdated Android"
                     " kernel forks.")
    if "downstream" in kernels and len(kernels) > 1:
        logging.info("Upstream kernels (mainline, stable, ...) get security"
                     " updates, but may have less working features than"
                     " downstream kernels.")

    # List kernels
    logging.info("Available kernels (" + str(len(kernels)) + "):")
    for type in sorted(kernels.keys()):
        logging.info("* " + type + ": " + kernels[type])
    while True:
        ret = pmb.helpers.cli.ask(args, "Kernel", None, default, True)
        if ret in kernels.keys():
            return ret
        logging.fatal("ERROR: Invalid kernel specified, please type in one"
                      " from the list above.")
    return ret


def ask_for_device_nonfree(args, device):
    """
    Ask the user about enabling proprietary firmware (e.g. Wifi) and userland
    (e.g. GPU drivers). All proprietary components are in subpackages
    $pkgname-nonfree-firmware and $pkgname-nonfree-userland, and we show the
    description of these subpackages (so they can indicate which peripherals
    are affected).

    :returns: answers as dict, e.g. {"firmware": True, "userland": False}
    """
    # Parse existing APKBUILD or return defaults (when called from test case)
    apkbuild_path = args.aports + "/device/device-" + device + "/APKBUILD"
    ret = {"firmware": args.nonfree_firmware,
           "userland": args.nonfree_userland}
    if not os.path.exists(apkbuild_path):
        return ret
    apkbuild = pmb.parse.apkbuild(args, apkbuild_path)

    # Only run when there is a "nonfree" subpackage
    nonfree_found = False
    for subpackage in apkbuild["subpackages"]:
        if subpackage.startswith("device-" + device + "-nonfree"):
            nonfree_found = True
    if not nonfree_found:
        return ret

    # Short explanation
    logging.info("This device has proprietary components, which trade some of"
                 " your freedom with making more peripherals work.")
    logging.info("We would like to offer full functionality without hurting"
                 " your freedom, but this is currently not possible for your"
                 " device.")

    # Ask for firmware and userland individually
    for type in ["firmware", "userland"]:
        subpkgname = "device-" + device + "-nonfree-" + type
        if subpkgname in apkbuild["subpackages"]:
            subpkgdesc = pmb.parse._apkbuild.subpkgdesc(apkbuild_path,
                                                        "nonfree_" + type)
            logging.info(subpkgname + ": " + subpkgdesc)
            ret[type] = pmb.helpers.cli.confirm(args, "Enable this package?",
                                                default=ret[type])
    return ret


def ask_for_device(args):
    devices = sorted(pmb.helpers.devices.list_codenames(args))
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
            if device == args.device:
                raise RuntimeError(
                    "This device does not exist anymore, check"
                    " <https://postmarketos.org/renamed>"
                    " to see if it was renamed")
            logging.info("You are about to do a new device port for '" +
                         device + "'.")
            if not pmb.helpers.cli.confirm(args, default=True):
                continue

            pmb.aportgen.generate(args, "device-" + device)
            pmb.aportgen.generate(args, "linux-" + device)
        break

    kernel = ask_for_device_kernel(args, device)
    nonfree = ask_for_device_nonfree(args, device)
    return (device, device_exists, kernel, nonfree)


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


def ask_for_hostname(args, device):
    while True:
        ret = pmb.helpers.cli.ask(args, "Device hostname (short form, e.g. 'foo')",
                                  None, (args.hostname or device), True)
        if not pmb.helpers.other.validate_hostname(ret):
            continue
        # Don't store device name in user's config (gets replaced in install)
        if ret == device:
            return ""
        return ret


def ask_for_ssh_keys(args):
    if not len(glob.glob(os.path.expanduser("~/.ssh/id_*.pub"))):
        return False
    return pmb.helpers.cli.confirm(args,
                                   "Would you like to copy your SSH public keys to the device?",
                                   default=args.ssh_keys)


def frontend(args):
    # Work folder (needs to be first, so we can create chroots early)
    cfg = pmb.config.load(args)
    work, work_exists = ask_for_work_path(args)
    cfg["pmbootstrap"]["work"] = work

    # Update args and save config (so chroots and 'pmbootstrap log' work)
    pmb.helpers.args.update_work(args, work)
    pmb.config.save(args, cfg)

    # Clone pmaports
    pmb.config.pmaports.init(args)

    # Device
    device, device_exists, kernel, nonfree = ask_for_device(args)
    cfg["pmbootstrap"]["device"] = device
    cfg["pmbootstrap"]["kernel"] = kernel
    cfg["pmbootstrap"]["nonfree_firmware"] = str(nonfree["firmware"])
    cfg["pmbootstrap"]["nonfree_userland"] = str(nonfree["userland"])

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
    extra = pmb.helpers.cli.ask(args, "Extra packages", None,
                                args.extra_packages,
                                validation_regex="^([-.+\w]+)(,[-.+\w]+)*$")
    cfg["pmbootstrap"]["extra_packages"] = extra

    # Configure timezone info
    cfg["pmbootstrap"]["timezone"] = ask_for_timezone(args)

    # Hostname
    cfg["pmbootstrap"]["hostname"] = ask_for_hostname(args, device)

    # SSH keys
    cfg["pmbootstrap"]["ssh_keys"] = str(ask_for_ssh_keys(args))

    # pmaports path (if users change it with: 'pmbootstrap --aports=... init')
    cfg["pmbootstrap"]["aports"] = args.aports

    # Save config
    pmb.config.save(args, cfg)

    # Zap existing chroots
    if (work_exists and device_exists and
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
