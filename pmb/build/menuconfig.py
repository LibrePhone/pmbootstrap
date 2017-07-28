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


def menuconfig(args, pkgname, arch):
    # Read apkbuild
    aport = pmb.build.find_aport(args, pkgname, False)
    if not aport:
        raise RuntimeError("Package " + pkgname + ": Could not find aport!")
    apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")

    # Set up build tools and makedepends
    pmb.build.init(args)
    depends = apkbuild["makedepends"] + ["ncurses-dev"]
    pmb.chroot.apk.install(args, depends, build=False)

    # Patch and extract sources
    pmb.build.copy_to_buildpath(args, pkgname)
    logging.info("(native) extract kernel source")
    pmb.chroot.user(args, ["abuild", "unpack"], "native", "/home/user/build")
    logging.info("(native) apply patches")
    pmb.chroot.user(args, ["abuild", "prepare"], "native", "/home/user/build",
                    log=False)

    # Run abuild menuconfig
    cmd = []
    environment = {"CARCH": arch, "TERM": "xterm"}
    for key, value in environment.items():
        cmd += [key + "=" + value]
    cmd += ["abuild", "-d", "menuconfig"]
    logging.info("(native) run menuconfig")
    pmb.chroot.user(args, cmd, "native", "/home/user/build", log=False)

    # Update config + checksums
    logging.info("copy kernel config back to aport-folder")
    source = args.work + "/chroot_native/home/user/build/src/build/.config"
    if not os.path.exists(source):
        raise RuntimeError("No kernel config generated!")
    target = aport + "/config-" + apkbuild["_flavor"] + "." + arch
    pmb.helpers.run.user(args, ["cp", source, target])
    pmb.build.checksum(args, pkgname)
