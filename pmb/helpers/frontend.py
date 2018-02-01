#!/usr/bin/env python3

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

import glob
import json
import logging
import os
import sys

import pmb.aportgen
import pmb.build
import pmb.build.autodetect
import pmb.config
import pmb.chroot
import pmb.chroot.initfs
import pmb.chroot.other
import pmb.flasher
import pmb.helpers.logging
import pmb.helpers.other
import pmb.helpers.pkgrel_bump
import pmb.helpers.repo
import pmb.helpers.run
import pmb.install
import pmb.parse
import pmb.qemu


def _build_verify_usage_device_package(args, pkgname):
    """
    Detect if the user is about to build a device- package for the wrong
    architecture. The package is noarch, but the dependencies (kernel!) will get
    pulled in with the same arch as dependency.
    """
    # Skip non-device-packages
    if not pkgname.startswith("device-"):
        return

    # Only continue when the --arch parameter is *not* the device architecture
    deviceinfo = args.aports + "/device/" + pkgname + "/deviceinfo"
    if not os.path.exists(deviceinfo):
        return
    device = pkgname.split("-", 1)[1]
    arch = pmb.parse.deviceinfo(args, device)["arch"]
    if args.arch == arch:
        return

    # Abort with a big note
    logging.info("Dependency handling in 'pmbootstrap build' has been"
                 " changed.")
    logging.info("Previously we only built and installed the 'makedepends'"
                 " from the APKBUILDs, now we use the 'depends', too.")
    logging.info("")
    logging.info("Your options:")
    logging.info("* Ignore depends (fast, old behavior, may cause problems"
                 " with some packages):")
    logging.info("  pmbootstrap build " + pkgname + " -i")
    logging.info("* Build with depends (kernel!) and specify the right"
                 " architecture:")
    logging.info("  pmbootstrap build " + pkgname + " --arch=" + arch)
    logging.info("")
    logging.info("This change was necessary to be more compatible with Alpine's"
                 " abuild.")
    logging.info("The default architecture is the native one (" +
                 args.arch_native + " in your case), so you need to overwrite")
    logging.info("it now to get the kernel dependency of your device package"
                 " for the right architecture.")
    logging.info("Sorry for the inconvenience.")
    logging.info("")
    raise RuntimeError("Missing -i or --arch parameter")


def _parse_flavor(args):
    """
    Verify the flavor argument if specified, or return a default value.
    """
    # Make sure, that at least one kernel is installed
    suffix = "rootfs_" + args.device
    pmb.chroot.apk.install(args, ["device-" + args.device], suffix)

    # Parse and verify the flavor argument
    flavor = args.flavor
    flavors = pmb.chroot.other.kernel_flavors_installed(args, suffix)
    if flavor:
        if flavor not in flavors:
            raise RuntimeError("No kernel installed with flavor " + flavor + "!" +
                               " Run 'pmbootstrap flasher list_flavors' to get a list.")
        return flavor
    if not len(flavors):
        raise RuntimeError(
            "No kernel flavors installed in chroot " + suffix + "! Please let"
            " your device package depend on a package starting with 'linux-'.")
    return flavors[0]


def _parse_suffix(args):
    if "rootfs" in args and args.rootfs:
        return "rootfs_" + args.device
    elif args.buildroot:
        if args.buildroot == "device":
            return "buildroot_" + args.deviceinfo["arch"]
        else:
            return "buildroot_" + args.buildroot
    elif args.suffix:
        return args.suffix
    else:
        return "native"


def aportgen(args):
    for package in args.packages:
        logging.info("Generate aport: " + package)
        pmb.aportgen.generate(args, package)


def build(args):
    # Strict mode: zap everything
    if args.strict:
        pmb.chroot.zap(args, False)

    # Detect wrong usage for device- packages
    if not args.ignore_depends:
        for package in args.packages:
            _build_verify_usage_device_package(args, package)

    # Build all packages
    for package in args.packages:
        arch_package = args.arch or pmb.build.autodetect.arch(args, package)
        if not pmb.build.package(args, package, arch_package, args.force,
                                 args.strict):
            logging.info("NOTE: Package '" + package + "' is up to date. Use"
                         " 'pmbootstrap build " + package + " --force'"
                         " if needed.")


def build_init(args):
    suffix = _parse_suffix(args)
    pmb.build.init(args, suffix)


def checksum(args):
    for package in args.packages:
        pmb.build.checksum(args, package)


def chroot(args):
    suffix = _parse_suffix(args)
    pmb.chroot.apk.check_min_version(args, suffix)
    logging.info("(" + suffix + ") % " + " ".join(args.command))
    pmb.chroot.root(args, args.command, suffix, log=False)


def config(args):
    keys = pmb.config.config_keys
    if args.name and args.name not in keys:
        logging.info("NOTE: Valid config keys: " + ", ".join(keys))
        raise RuntimeError("Invalid config key: " + args.name)

    cfg = pmb.config.load(args)
    if args.value:
        cfg["pmbootstrap"][args.name] = args.value
        logging.info("Config changed: " + args.name + "='" + args.value + "'")
        pmb.config.save(args, cfg)
    elif args.name:
        value = cfg["pmbootstrap"].get(args.name, "")
        print(value)
    else:
        cfg.write(sys.stdout)

    # Don't write the "Done" message
    pmb.helpers.logging.disable()


def index(args):
    pmb.build.index_repo(args)


def initfs(args):
    pmb.chroot.initfs.frontend(args)


def install(args):
    if args.rsync and args.full_disk_encryption:
        raise ValueError("Installation using rsync is not compatible with full"
                         " disk encryption.")
    if args.rsync and not args.sdcard:
        raise ValueError("Installation using rsync only works on sdcard.")

    pmb.install.install(args)


def flasher(args):
    pmb.flasher.frontend(args)


def export(args):
    pmb.export.frontend(args)


def menuconfig(args):
    pmb.build.menuconfig(args, args.package)


def update(args):
    pmb.helpers.repo.update(args, True)


def newapkbuild(args):
    if not len(args.args_passed):
        logging.info("See 'pmbootstrap newapkbuild -h' for usage information.")
        raise RuntimeError("No arguments to pass to newapkbuild specified!")
    pmb.build.newapkbuild(args, args.folder, args.args_passed)


def kconfig_check(args):
    # Default to all kernel packages
    packages = args.packages
    if not packages:
        for aport in glob.glob(args.aports + "/*/linux-*"):
            packages.append(os.path.basename(aport).split("linux-")[1])

    # Iterate over all kernels
    error = False
    packages.sort()
    for package in packages:
        if not pmb.parse.kconfig.check(args, package, details=True):
            error = True

    # At least one failure
    if error:
        raise RuntimeError("kconfig_check failed!")


def apkbuild_parse(args):
    # Default to all packages
    packages = args.packages
    if not packages:
        for apkbuild in glob.glob(args.aports + "/*/*/APKBUILD"):
            packages.append(os.path.basename(os.path.dirname(apkbuild)))

    # Iterate over all packages
    packages.sort()
    for package in packages:
        print(package + ":")
        aport = pmb.build.other.find_aport(args, package)
        path = aport + "/APKBUILD"
        print(json.dumps(pmb.parse.apkbuild(args, path), indent=4,
                         sort_keys=True))


def apkindex_parse(args):
    result = pmb.parse.apkindex.parse(args, args.apkindex_path)
    if args.package:
        if args.package not in result:
            raise RuntimeError("Package not found in the APKINDEX: " +
                               args.package)
        result = result[args.package]
    print(json.dumps(result, indent=4))


def pkgrel_bump(args):
    would_bump = True
    if args.auto:
        would_bump = pmb.helpers.pkgrel_bump.auto(args, args.dry)
    else:
        # Each package must exist
        for package in args.packages:
            pmb.build.other.find_aport(args, package)

        # Increase pkgrel
        for package in args.packages:
            pmb.helpers.pkgrel_bump.package(args, package, dry=args.dry)

    if args.dry and would_bump:
        logging.info("Pkgrels of package(s) would have been bumped!")
        sys.exit(1)


def qemu(args):
    pmb.qemu.run(args)


def shutdown(args):
    pmb.chroot.shutdown(args)


def stats(args):
    # Chroot suffix
    suffix = "native"
    if args.arch != args.arch_native:
        suffix = "buildroot_" + args.arch

    # Install ccache and display stats
    pmb.chroot.apk.install(args, ["ccache"], suffix)
    logging.info("(" + suffix + ") % ccache -s")
    pmb.chroot.user(args, ["ccache", "-s"], suffix, log=False)


def log(args):
    if args.clear_log:
        pmb.helpers.run.user(args, ["truncate", "-s", "0", args.log],
                             log=False)
    pmb.helpers.run.user(args, ["tail", "-f", args.log, "-n", args.lines],
                         log=False)


def log_distccd(args):
    logpath = "/home/pmos/distccd.log"
    if args.clear_log:
        pmb.chroot.user(args, ["truncate", "-s", "0", logpath], log=False)
    pmb.chroot.user(args, ["tail", "-f", logpath, "-n", args.lines], log=False)


def zap(args):
    pmb.chroot.zap(args, dry=args.dry, packages=args.packages, http=args.http,
                   mismatch_bins=args.mismatch_bins, old_bins=args.old_bins,
                   distfiles=args.distfiles)

    # Don't write the "Done" message
    pmb.helpers.logging.disable()


def bootimg_analyze(args):
    bootimg = pmb.parse.bootimg(args, args.path)
    tmp_output = "Put these variables in the deviceinfo file of your device:\n"
    for line in pmb.aportgen.device.generate_deviceinfo_fastboot_content(args, bootimg).split("\n"):
        tmp_output += "\n" + line.lstrip()
    logging.info(tmp_output)
