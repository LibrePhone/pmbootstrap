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
import os
import logging

import pmb.build
import pmb.build.autodetect
import pmb.build.checksum
import pmb.chroot
import pmb.chroot.apk
import pmb.chroot.other
import pmb.helpers.pmaports
import pmb.helpers.run
import pmb.parse


def get_arch(args, apkbuild):
    """
    Get the architecture, that the user wants to run menuconfig on, depending on
    the APKBUILD and on the --arch parameter.

    :param apkbuild: looks like: {"pkgname": "linux-...",
                                  "arch": ["x86_64", "armhf", "aarch64"]}
                     or: {"pkgname": "linux-...", "arch": ["armhf"]}
    """
    pkgname = apkbuild["pkgname"]

    # Multiple architectures (requires --arch)
    if len(apkbuild["arch"]) > 1:
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


def get_outputdir(args, pkgname):
    """
    Get the folder for the kernel compilation output.
    For most APKBUILDs, this is $builddir. But some older ones still use
    $srcdir/build (see the discussion in #1551).
    """
    # Old style ($srcdir/build)
    ret = "/home/pmos/build/src/build"
    chroot = args.work + "/chroot_native"
    if os.path.exists(chroot + ret + "/.config"):
        logging.warning("*****")
        logging.warning("NOTE: The code in this linux APKBUILD is pretty old."
                        " Consider making a backup and migrating to a modern"
                        " version with: pmbootstrap aportgen " + pkgname)
        logging.warning("*****")

        return ret

    # New style ($builddir)
    cmd = "srcdir=/home/pmos/build/src source APKBUILD; echo $builddir"
    ret = pmb.chroot.user(args, ["sh", "-c", cmd],
                          "native", "/home/pmos/build",
                          output_return=True).rstrip()
    if os.path.exists(chroot + ret + "/.config"):
        return ret

    # Not found
    raise RuntimeError("Could not find the kernel config. Consider making a"
                       " backup of your APKBUILD and recreating it from the"
                       " template with: pmbootstrap aportgen " + pkgname)


def menuconfig(args, pkgname):
    # Pkgname: allow omitting "linux-" prefix
    if pkgname.startswith("linux-"):
        pkgname_ = pkgname.split("linux-")[1]
        logging.info("PROTIP: You can simply do 'pmbootstrap kconfig edit " +
                     pkgname_ + "'")
    else:
        pkgname = "linux-" + pkgname

    # Read apkbuild
    aport = pmb.helpers.pmaports.find(args, pkgname)
    apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
    arch = get_arch(args, apkbuild)
    kopt = "menuconfig"

    # Set up build tools and makedepends
    pmb.build.init(args)
    depends = apkbuild["makedepends"]
    kopt = "menuconfig"
    copy_xauth = False
    if args.xconfig:
        depends += ["qt-dev", "font-noto"]
        kopt = "xconfig"
        copy_xauth = True
    elif args.gconfig:
        depends += ["gtk+2.0-dev", "glib-dev", "libglade-dev", "font-noto"]
        kopt = "gconfig"
        copy_xauth = True
    else:
        depends += ["ncurses-dev"]
    pmb.chroot.apk.install(args, depends)

    # Copy host's .xauthority into native
    if copy_xauth:
        pmb.chroot.other.copy_xauthority(args)

    # Patch and extract sources
    pmb.build.copy_to_buildpath(args, pkgname)
    logging.info("(native) extract kernel source")
    pmb.chroot.user(args, ["abuild", "unpack"], "native", "/home/pmos/build")
    logging.info("(native) apply patches")
    pmb.chroot.user(args, ["abuild", "prepare"], "native",
                    "/home/pmos/build", output="interactive",
                    env={"CARCH": arch})

    # Run make menuconfig
    outputdir = get_outputdir(args, pkgname)
    logging.info("(native) make " + kopt)
    pmb.chroot.user(args, ["make", kopt], "native",
                    outputdir, output="tui",
                    env={"ARCH": pmb.parse.arch.alpine_to_kernel(arch),
                         "DISPLAY": os.environ.get("DISPLAY"),
                         "XAUTHORITY": "/home/pmos/.Xauthority"})

    # Find the updated config
    source = args.work + "/chroot_native" + outputdir + "/.config"
    if not os.path.exists(source):
        raise RuntimeError("No kernel config generated: " + source)

    # Update the aport (config and checksum)
    logging.info("Copy kernel config back to aport-folder")
    config = "config-" + apkbuild["_flavor"] + "." + arch
    target = aport + "/" + config
    pmb.helpers.run.user(args, ["cp", source, target])
    pmb.build.checksum(args, pkgname)

    # Check config
    pmb.parse.kconfig.check(args, apkbuild["_flavor"], details=True)
