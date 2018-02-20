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
import os

import pmb.build.other
import pmb.helpers.file
import pmb.helpers.repo
import pmb.parse


def package(args, pkgname, reason="", dry=False):
    """
    Increase the pkgrel in the APKBUILD of a specific package.

    :param pkgname: name of the package
    :param reason: string to display as reason why it was increased
    :param dry: don't modify the APKBUILD, just print the message
    """
    # Current and new pkgrel
    path = pmb.build.other.find_aport(args, pkgname) + "/APKBUILD"
    apkbuild = pmb.parse.apkbuild(args, path)
    pkgrel = int(apkbuild["pkgrel"])
    pkgrel_new = pkgrel + 1

    # Display the message, bail out in dry mode
    logging.info("Increase '" + pkgname + "' pkgrel (" + str(pkgrel) + " -> " +
                 str(pkgrel_new) + ")" + reason)
    if dry:
        return

    # Increase
    old = "\npkgrel=" + str(pkgrel) + "\n"
    new = "\npkgrel=" + str(pkgrel_new) + "\n"
    pmb.helpers.file.replace(path, old, new)

    # Verify
    del(args.cache["apkbuild"][path])
    apkbuild = pmb.parse.apkbuild(args, path)
    if int(apkbuild["pkgrel"]) != pkgrel_new:
        raise RuntimeError("Failed to bump pkgrel for package '" + pkgname +
                           "'. Make sure that there's a line with exactly the"
                           " string '" + old + "' and nothing else in: " +
                           path)


def auto_apkindex_files(args):
    """
    Get the paths to the APKINDEX files, that need to be analyzed, sorted by
    arch. Relevant are the local pmbootstrap generated APKINDEX as well as the
    APKINDEX from the pmOS binary repo.
.
    :returns: {"armhf": "...../APKINDEX.tar.gz", ...}
    """
    pmb.helpers.repo.update(args)
    ret = {}
    for arch in pmb.config.build_device_architectures:
        ret[arch] = []
        local = args.work + "/packages/" + arch + "/APKINDEX.tar.gz"
        if os.path.exists(local):
            ret[arch].append(local)

        if args.mirror_postmarketos:
            path = (args.work + "/cache_apk_" + arch + "/APKINDEX." +
                    pmb.helpers.repo.hash(args.mirror_postmarketos) + ".tar.gz")
            ret[arch].append(path)
    return ret


def auto_apkindex_package(args, pkgname, aport_version, apkindex, arch,
                          dry=False):
    """
    Bump the pkgrel of a specific package if it is outdated in the given
    APKINDEX.

    :param pkgname: name of the package
    :param aport_version: combination of pkgver and pkgrel (e.g. "1.23-r1")
    :param apkindex: path to the APKINDEX.tar.gz file
    :param arch: the architecture, e.g. "armhf"
    :param dry: don't modify the APKBUILD, just print the message
    :returns: True when there was an APKBUILD that needed to be changed.
    """
    # Binary package
    binary = pmb.parse.apkindex.package(args, pkgname, must_exist=False,
                                        indexes=[apkindex])
    if not binary:
        return

    # Skip when aport version != binary package version
    compare = pmb.parse.version.compare(aport_version,
                                        binary["version"])
    if compare == -1:
        logging.warning("WARNING: Skipping '" + pkgname +
                        "' in index " + apkindex + ", because the"
                        " binary version " + binary["version"] +
                        " is higher than the aport version " +
                        aport_version)
        return
    if compare == 1:
        logging.verbose(pkgname + ": aport version bigger than the"
                        " one in the APKINDEX, skipping:" +
                        apkindex)
        return

    # Find missing depends
    logging.verbose(pkgname + ": checking depends: " +
                    ",".join(binary["depends"]))
    missing = []
    for depend in binary["depends"]:
        providers = pmb.parse.apkindex.providers(args, depend, arch,
                                                 must_exist=False)
        if providers == {}:
            # We're only interested in missing depends starting with "so:"
            # (which means dynamic libraries that the package was linked
            # against) and packages for which no aport exists.
            if (depend.startswith("so:") or
                    not pmb.build.other.find_aport(args, depend)):
                missing.append(depend)

    # Increase pkgrel
    if len(missing):
        package(args, pkgname, reason=", missing depend(s): " +
                ", ".join(missing), dry=dry)
        return True


def auto(args, dry=False):
    """
    :returns: True when there was an APKBUILD that needed to be changed.
    """
    # Get APKINDEX files
    arch_apkindexes = auto_apkindex_files(args)

    # Iterate over aports
    ret = False
    for aport in glob.glob(args.aports + "/*/*"):
        pkgname = os.path.basename(aport)
        aport = pmb.parse.apkbuild(args, aport + "/APKBUILD")
        aport_version = aport["pkgver"] + "-r" + aport["pkgrel"]

        for arch, apkindexes in arch_apkindexes.items():
            for apkindex in apkindexes:
                if auto_apkindex_package(args, pkgname, aport_version, apkindex,
                                         arch, dry):
                    ret = True
    return ret
