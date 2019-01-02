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
import os

import pmb.helpers.file
import pmb.helpers.pmaports
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
    path = pmb.helpers.pmaports.find(args, pkgname) + "/APKBUILD"
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

    :returns: {"armhf": "...../APKINDEX.tar.gz", ...}
    """
    pmb.helpers.repo.update(args)
    ret = {}
    for arch in pmb.config.build_device_architectures:
        ret[arch] = []
        local = args.work + "/packages/" + arch + "/APKINDEX.tar.gz"
        if os.path.exists(local):
            ret[arch].append(local)

        for mirror in args.mirrors_postmarketos:
            path = (args.work + "/cache_apk_" + arch + "/APKINDEX." +
                    pmb.helpers.repo.hash(mirror) + ".tar.gz")
            ret[arch].append(path)
    return ret


def auto_apkindex_package(args, arch, aport, apk, dry=False):
    """
    Bump the pkgrel of a specific package if it is outdated in the given
    APKINDEX.

    :param arch: the architecture, e.g. "armhf"
    :param aport: parsed APKBUILD of the binary package's origin:
                  {"pkgname": ..., "pkgver": ..., "pkgrel": ..., ...}
    :param apk: information about the binary package from the APKINDEX:
                {"version": ..., "depends": [...], ...}
    :param dry: don't modify the APKBUILD, just print the message
    :returns: True when there was an APKBUILD that needed to be changed.
    """
    version_aport = aport["pkgver"] + "-r" + aport["pkgrel"]
    version_apk = apk["version"]
    pkgname = aport["pkgname"]

    # Skip when aport version != binary package version
    compare = pmb.parse.version.compare(version_aport, version_apk)
    if compare == -1:
        logging.warning("{}: skipping, because the aport version {} is lower"
                        " than the binary version {}".format(pkgname,
                                                             version_aport,
                                                             version_apk))
        return
    if compare == 1:
        logging.verbose("{}: skipping, because the aport version {} is higher"
                        " than the binary version {}".format(pkgname,
                                                             version_aport,
                                                             version_apk))
        return

    # Find missing depends
    depends = apk["depends"]
    logging.verbose("{}: checking depends: {}".format(pkgname,
                                                      ", ".join(depends)))
    missing = []
    for depend in depends:
        providers = pmb.parse.apkindex.providers(args, depend, arch,
                                                 must_exist=False)
        if providers == {}:
            # We're only interested in missing depends starting with "so:"
            # (which means dynamic libraries that the package was linked
            # against) and packages for which no aport exists.
            if (depend.startswith("so:") or
                    not pmb.helpers.pmaports.find(args, depend, False)):
                missing.append(depend)

    # Increase pkgrel
    if len(missing):
        package(args, pkgname, reason=", missing depend(s): " +
                ", ".join(missing), dry=dry)
        return True


def auto(args, dry=False):
    """
    :returns: list of aport names, where the pkgrel needed to be changed
    """
    ret = []
    for arch, paths in auto_apkindex_files(args).items():
        for path in paths:
            logging.info("scan " + path)
            index = pmb.parse.apkindex.parse(args, path, False)
            for pkgname, apk in index.items():
                origin = apk["origin"]
                # Only increase once!
                if origin in ret:
                    logging.verbose("{}: origin '{}' found again".format(pkgname,
                                                                         origin))
                    continue
                aport_path = pmb.helpers.pmaports.find(args, origin, False)
                if not aport_path:
                    logging.warning("{}: origin '{}' aport not found".format(
                                    pkgname, origin))
                    continue
                aport = pmb.parse.apkbuild(args, aport_path + "/APKBUILD")
                if auto_apkindex_package(args, arch, aport, apk, dry):
                    ret.append(pkgname)
    return ret
