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
import glob
import logging

import pmb.chroot
import pmb.helpers.run


def zap(args, confirm=True, packages=False, http=False, mismatch_bins=False):
    pmb.chroot.shutdown(args)
    patterns = [
        "chroot_native",
        "chroot_buildroot_*",
        "chroot_rootfs_*",
    ]

    # Only ask for removal, if the user specificed the extra '-p' switch.
    # Deleting the packages by accident is really annoying.
    if packages:
        patterns += ["packages"]
    if http:
        patterns += ["cache_http"]

    for pattern in patterns:
        pattern = os.path.realpath(args.work + "/" + pattern)
        matches = glob.glob(pattern)
        for match in matches:
            if not confirm or pmb.helpers.cli.confirm(args, "Remove " + match + "?"):
                pmb.helpers.run.root(args, ["rm", "-rf", match])

    if mismatch_bins:
        binaries(args)
        # Re-index repos since apks may have been removed
        pmb.build.other.index_repo(args)


def binaries(args):
    for arch_dir in os.scandir(os.path.realpath(args.work + "/packages/")):
        arch = arch_dir.name
        arch_pkg_path = os.path.realpath(args.work) + "/packages/" + arch
        bin_apks = pmb.parse.apkindex.parse(args, arch_pkg_path + "/APKINDEX.tar.gz")
        for bin_apk in bin_apks:
            bin_pkgname = bin_apks[bin_apk]["pkgname"]
            bin_version = bin_apks[bin_apk]["version"]
            bin_apk_path = arch_pkg_path + "/" + bin_pkgname + "-" + bin_version + ".apk"
            # Do not fail if unable to find aport
            aport = pmb.build.other.find_aport(args, bin_pkgname, False)
            if not aport:
                logging.warning("WARNING: Could not resolve aport for package " + bin_apk_path)
                continue
            apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
            aport_version = apkbuild["pkgver"] + "-r" + apkbuild["pkgrel"]
            # Clear out any binary apks that do not match what is in aports
            if pmb.parse.version.compare(bin_version, aport_version) and os.path.exists(bin_apk_path):
                logging.info("Remove mismatched binary package (aports version: " +
                             aport_version + "): " + arch + "/" + bin_pkgname + "-" +
                             bin_version + ".apk")
                pmb.helpers.run.root(args, ["rm", bin_apk_path])
