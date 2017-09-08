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
import pmb.build.buildinfo
import pmb.chroot
import pmb.chroot.apk
import pmb.chroot.distccd
import pmb.parse
import pmb.parse.arch


def package(args, pkgname, carch, force=False, buildinfo=False, strict=False):
    """
    Build a package with Alpine Linux' abuild.

    :param force: even build, if not necessary
    :returns: output path relative to the packages folder
    """
    # Get aport, skip upstream only packages
    aport = pmb.build.find_aport(args, pkgname, False)
    if not aport:
        if pmb.parse.apkindex.read_any_index(args, pkgname, carch):
            return
        raise RuntimeError("Package " + pkgname + ": Could not find aport,"
                           " and could not find this package in any APKINDEX!")

    # Autodetect the build environment
    apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
    pkgname = apkbuild["pkgname"]
    carch_buildenv = pmb.build.autodetect.carch(args, apkbuild, carch, strict)
    suffix = pmb.build.autodetect.suffix(args, apkbuild, carch_buildenv)
    cross = pmb.build.autodetect.crosscompile(args, apkbuild, carch_buildenv,
                                              suffix)

    # Skip already built versions
    if not force and not pmb.build.is_necessary(args, carch, apkbuild):
        return

    # Initialize build environment, install/build makedepends
    pmb.build.init(args, suffix)
    if len(apkbuild["makedepends"]):
        if strict:
            for makedepend in apkbuild["makedepends"]:
                package(args, makedepend, carch_buildenv, strict=True)
        else:
            pmb.chroot.apk.install(args, apkbuild["makedepends"], suffix)
    if cross:
        pmb.chroot.apk.install(args, ["gcc-" + carch_buildenv,
                                      "g++-" + carch_buildenv,
                                      "ccache-cross-symlinks"])
        if cross == "distcc":
            pmb.chroot.apk.install(args, ["distcc"], suffix=suffix,
                                   build=False)
            pmb.chroot.distccd.start(args, carch_buildenv)

    # Avoid re-building for circular dependencies
    if not force and not pmb.build.is_necessary(args, carch, apkbuild):
        return

    # Configure abuild.conf
    pmb.build.other.configure_abuild(args, suffix)

    # Generate output name, log build message
    output = (carch_buildenv + "/" + apkbuild["pkgname"] + "-" +
              apkbuild["pkgver"] + "-r" + apkbuild["pkgrel"] + ".apk")
    logging.info("(" + suffix + ") build " + output)

    # Sanity check
    if cross == "native" and "!tracedeps" not in apkbuild["options"]:
        logging.info("WARNING: Option !tracedeps is not set, but we're"
                     " cross-compiling in the native chroot. This will probably"
                     " fail!")

    # Run abuild
    pmb.build.copy_to_buildpath(args, pkgname, suffix)
    cmd = []
    env = {"CARCH": carch_buildenv}
    if cross == "native":
        hostspec = pmb.parse.arch.alpine_to_hostspec(carch_buildenv)
        env["CROSS_COMPILE"] = hostspec + "-"
        env["CC"] = hostspec + "-gcc"
    if cross == "distcc":
        env["PATH"] = "/usr/lib/distcc/bin:" + pmb.config.chroot_path
        env["DISTCC_HOSTS"] = "127.0.0.1:" + args.port_distccd
    for key, value in env.items():
        cmd += [key + "=" + value]
    cmd += ["abuild"]
    if strict:
        cmd += ["-r"]  # install depends with abuild
    else:
        cmd += ["-d"]  # do not install depends with abuild
    if force:
        cmd += ["-f"]
    pmb.chroot.user(args, cmd, suffix, "/home/user/build")

    # Verify output file
    path = args.work + "/packages/" + output
    if not os.path.exists(path):
        raise RuntimeError("Package not found after build: " + path)

    # Create .buildinfo.json file
    if buildinfo:
        logging.info("(" + suffix + ") generate " + output + ".buildinfo.json")
        pmb.build.buildinfo.write(args, output, carch_buildenv, suffix,
                                  apkbuild)

    # Symlink noarch packages
    if "noarch" in apkbuild["arch"]:
        pmb.build.symlink_noarch_package(args, output)

    # Clean up (APKINDEX cache, depends when strict)
    pmb.parse.apkindex.clear_cache(args, args.work + "/packages/" +
                                   carch_buildenv + "/APKINDEX.tar.gz")
    if strict:
        logging.info("(" + suffix + ") uninstall makedepends")
        pmb.chroot.user(args, ["abuild", "undeps"], suffix, "/home/user/build")

    return output
