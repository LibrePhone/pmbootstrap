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
import os
import logging

import pmb.build
import pmb.build.autodetect
import pmb.build.checksum
import pmb.chroot
import pmb.chroot.apk
import pmb.helpers.run
import pmb.parse


def get_arch(args, apkbuild):
    """
    Get the architecture, that the user wants to run menuconfig on, depending on
    the APKBUILD and on the --arch parameter.

    :param apkbuild: looks like: {"pkgname": "linux-...", "arch": ["all"]}
                     or: {"pkgname": "linux-...", "arch": ["armhf"]}
    """
    pkgname = apkbuild["pkgname"]

    # Multiple architectures (requires --arch)
    if "all" in apkbuild["arch"]:
        if args.arch is None:
            raise RuntimeError("Package '" + pkgname + "' supports multiple"
                               " architectures, please use '--arch' to specify"
                               " the desired architecture.")
        return args.arch

    # Single architecture (--arch must be unset or match)
    if args.arch is None or args.arch == apkbuild["arch"][0]:
        return apkbuild["arch"][0]
    raise RuntimeError("Package '" + pkgname + "' only supports the '" +
                       apkbuild["arch"][0] + "' architecture.")


def menuconfig(args, pkgname):
    # Pkgname: allow omitting "linux-" prefix
    if pkgname.startswith("linux-"):
        pkgname_ = pkgname.split("linux-")[1]
        logging.info("PROTIP: You can simply do 'pmbootstrap menuconfig " +
                     pkgname_ + "'")
    else:
        pkgname = "linux-" + pkgname

    # Read apkbuild
    aport = pmb.build.find_aport(args, pkgname)
    apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
    arch = get_arch(args, apkbuild)

    # Set up build tools and makedepends
    pmb.build.init(args)
    depends = apkbuild["makedepends"] + ["ncurses-dev"]
    pmb.chroot.apk.install(args, depends)

    # Patch and extract sources
    pmb.build.copy_to_buildpath(args, pkgname)
    logging.info("(native) extract kernel source")
    pmb.chroot.user(args, ["abuild", "unpack"], "native", "/home/pmos/build")
    logging.info("(native) apply patches")
    pmb.chroot.user(args, ["CARCH=" + arch, "abuild", "prepare"], "native",
                    "/home/pmos/build", log=False)

    # Run abuild menuconfig
    cmd = []
    environment = {"CARCH": arch, "TERM": "xterm"}
    for key, value in environment.items():
        cmd += [key + "=" + value]
    cmd += ["abuild", "-d", "menuconfig"]
    logging.info("(native) run menuconfig")
    pmb.chroot.user(args, cmd, "native", "/home/pmos/build", log=False)

    # Update config + checksums
    config = "config-" + apkbuild["_flavor"] + "." + arch
    logging.info("Copy kernel config back to aport-folder")
    source = args.work + "/chroot_native/home/pmos/build/" + config
    if not os.path.exists(source):
        raise RuntimeError("No kernel config generated!")
    target = aport + "/" + config
    pmb.helpers.run.user(args, ["cp", source, target])
    pmb.build.checksum(args, pkgname)

    # Check config
    pmb.parse.kconfig.check(args, apkbuild["_flavor"], details=True)
