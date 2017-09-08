#!/usr/bin/env python3

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
import json
import sys

import pmb.aportgen
import pmb.build
import pmb.config
import pmb.challenge
import pmb.chroot
import pmb.chroot.initfs
import pmb.chroot.other
import pmb.flasher
import pmb.helpers.logging
import pmb.helpers.other
import pmb.helpers.run
import pmb.install
import pmb.parse
import pmb.qemu


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
    if args.rootfs:
        return "rootfs_" + args.device
    elif args.buildroot:
        return "buildroot_" + args.deviceinfo["arch"]
    elif args.suffix:
        return args.suffix
    else:
        return "native"


def aportgen(args):
    for package in args.packages:
        pmb.aportgen.generate(args, package)


def build(args):
    if args.strict:
        pmb.chroot.zap(args, False)
    for package in args.packages:
        pmb.build.package(args, package, args.arch, args.force,
                          args.buildinfo, args.strict)


def build_init(args):
    suffix = _parse_suffix(args)
    pmb.build.init(args, suffix)


def challenge(args):
    pmb.challenge.frontend(args)


def checksum(args):
    for package in args.packages:
        pmb.build.checksum(args, package)


def chroot(args):
    suffix = _parse_suffix(args)
    pmb.chroot.apk.check_min_version(args, suffix)
    logging.info("(" + suffix + ") % " + " ".join(args.command))
    pmb.chroot.root(args, args.command, suffix, log=False)


def config(args):
    pmb.helpers.logging.disable()
    if args.name and args.name not in pmb.config.defaults:
        valid_keys = ", ".join(sorted(pmb.config.defaults.keys()))
        print("The variable name you have specified is invalid.")
        print("The following are supported: " + valid_keys)
        sys.exit(1)

    cfg = pmb.config.load(args)
    if args.value:
        cfg["pmbootstrap"][args.name] = args.value
        pmb.config.save(args, cfg)
    elif args.name:
        value = cfg["pmbootstrap"].get(args.name, "")
        print(value)
    else:
        cfg.write(sys.stdout)


def index(args):
    pmb.build.index_repo(args)


def initfs(args):
    pmb.chroot.initfs.frontend(args)


def install(args):
    pmb.install.install(args)


def flasher(args):
    pmb.flasher.frontend(args)


def export(args):
    pmb.export.frontend(args)


def menuconfig(args):
    pmb.build.menuconfig(args, args.package, args.deviceinfo["arch"])


def parse_apkbuild(args):
    aport = pmb.build.other.find_aport(args, args.package)
    path = aport + "/APKBUILD"
    print(json.dumps(pmb.parse.apkbuild(args, path), indent=4))


def parse_apkindex(args):
    result = pmb.parse.apkindex.parse(args, args.apkindex_path)
    if args.package:
        if args.package not in result:
            raise RuntimeError("Package not found in the APKINDEX: " +
                               args.package)
        result = result[args.package]
    print(json.dumps(result, indent=4))


def qemu(args):
    pmb.qemu.run(args)


def shutdown(args):
    pmb.chroot.shutdown(args)


def stats(args):
    pmb.build.ccache_stats(args, args.arch)


def log(args):
    if args.clear_log:
        pmb.helpers.run.user(args, ["truncate", "-s", "0", args.log],
                             log=False)
    pmb.helpers.run.user(args, ["tail", "-f", args.log, "-n", args.lines],
                         log=False)


def log_distccd(args):
    logpath = "/home/user/distccd.log"
    if args.clear_log:
        pmb.chroot.user(args, ["truncate", "-s", "0", logpath], log=False)
    pmb.chroot.user(args, ["tail", "-f", logpath, "-n", args.lines], log=False)


def zap(args):
    pmb.chroot.zap(args, packages=args.packages, http=args.http,
                   mismatch_bins=args.mismatch_bins)
