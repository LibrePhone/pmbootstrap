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
import logging
import math
import os

import pmb.chroot
import pmb.helpers.run


def zap(args, confirm=True, dry=False, packages=False, http=False,
        mismatch_bins=False, old_bins=False, distfiles=False):
    """
    Shutdown everything inside the chroots (e.g. distccd, adb), umount
    everything and then safely remove folders from the work-directory.

    :param dry: Only show what would be deleted, do not delete for real
    :param packages: Remove *all* self-compiled packages (!)
    :param http: Clear the http cache (used e.g. for the initial apk download)
    :param mismatch_bins: Remove the packages, that have a different version
                          compared to what is in the aports folder.
    :param old_bins: Clean out outdated binary packages downloaded from
                     mirrors (e.g. from Alpine)
    :param distfiles: Clear the downloaded files cache

    NOTE: This function gets called in pmb/config/init.py, with only args.work
    and args.device set!
    """
    # Get current work folder size
    if not dry:
        pmb.chroot.shutdown(args)
        logging.debug("Calculate work folder size")
        size_old = pmb.helpers.other.folder_size(args, args.work)

    # Delete packages with a different version compared to aports, then re-index
    if mismatch_bins:
        zap_mismatch_bins(args, confirm, dry)

    # Delete outdated binary packages
    if old_bins:
        zap_old_bins(args, confirm, dry)

    pmb.chroot.shutdown(args)

    # Deletion patterns for folders inside args.work
    patterns = [
        "chroot_native",
        "chroot_buildroot_*",
        "chroot_rootfs_*",
    ]
    if packages:
        patterns += ["packages"]
    if http:
        patterns += ["cache_http"]
    if distfiles:
        patterns += ["cache_distfiles"]

    # Delete everything matching the patterns
    for pattern in patterns:
        pattern = os.path.realpath(args.work + "/" + pattern)
        matches = glob.glob(pattern)
        for match in matches:
            if not confirm or pmb.helpers.cli.confirm(args, "Remove " + match + "?"):
                logging.info("% rm -rf " + match)
                if not dry:
                    pmb.helpers.run.root(args, ["rm", "-rf", match])

    # Chroots were zapped, so no repo lists exist anymore
    args.cache["apk_repository_list_updated"].clear()

    # Print amount of cleaned up space
    if dry:
        logging.info("Dry run: nothing has been deleted")
    else:
        size_new = pmb.helpers.other.folder_size(args, args.work)
        mb = (size_old - size_new) / 1024 / 1024
        logging.info("Cleared up ~" + str(math.ceil(mb)) + " MB of space")


def zap_mismatch_bins(args, confirm=True, dry=False):
    if not os.path.exists(args.work + "/packages/"):
        return
    if confirm and not pmb.helpers.cli.confirm(args, "Remove packages that are newer than"
                                               " the corresponding package in aports?"):
        return

    reindex = False
    for apkindex_path in glob.glob(args.work + "/packages/*/APKINDEX.tar.gz"):
        apkindex = pmb.parse.apkindex.parse(args, apkindex_path)
        for pkgname, bin_data in apkindex.items():
            # Only real packages have apks, provided packages do not exist
            # (e.g. "so:libtest.so.1.2")
            if pkgname != bin_data["pkgname"]:
                continue
            origin = bin_data["origin"]
            version = bin_data["version"]
            arch = bin_data["arch"]

            # Apk path
            apk_path_short = arch + "/" + pkgname + "-" + version + ".apk"
            apk_path = args.work + "/packages/" + apk_path_short
            if not os.path.exists(apk_path):
                logging.info("WARNING: Package mentioned in index not"
                             " found: " + apk_path_short)
                continue

            # Aport path
            aport_path = pmb.build.other.find_aport(args, origin, False)
            if not aport_path:
                logging.info("% rm " + apk_path_short + " (" + origin +
                             " aport not found)")
                if not dry:
                    pmb.helpers.run.root(args, ["rm", apk_path])
                    reindex = True
                continue

            # Clear out any binary apks that do not match what is in aports
            apkbuild = pmb.parse.apkbuild(args, aport_path + "/APKBUILD")
            version_aport = apkbuild["pkgver"] + "-r" + apkbuild["pkgrel"]
            if version != version_aport:
                logging.info("% rm " + apk_path_short + " (" + origin +
                             " aport: " + version_aport + ")")
                if not dry:
                    pmb.helpers.run.root(args, ["rm", apk_path])
                    reindex = True

    if reindex:
        pmb.build.other.index_repo(args)


def zap_old_bins(args, confirm=True, dry=False):
    # Check whether we need to do anything
    paths = glob.glob(args.work + "/cache_apk_*")
    if not len(paths):
        return
    if confirm and not pmb.helpers.cli.confirm(args, "Remove outdated binary packages?"):
        return

    # Iterate over existing apk caches
    for path in paths:
        arch = os.path.basename(path).split("_", 2)[2]
        chroot = "native" if arch == args.arch_native else "buildroot_" + arch

        # Clean the cache with apk
        logging.info("(" + chroot + ") apk -v cache clean")
        if not dry:
            pmb.chroot.root(args, ["apk", "-v", "cache", "clean"], chroot)
