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
import pmb.chroot
import pmb.chroot.apk
import pmb.parse.apkindex


def apkindex(args, pkgname, arch):
    """
    Non-recursively get the dependencies of one package in any APKINDEX.
    """
    index_data = pmb.parse.apkindex.read_any_index(args, pkgname, arch)
    if index_data:
        return index_data["depends"]
    else:
        return None


def recurse_error_message(pkgname, in_aports, in_apkindexes):
    ret = "Could not find package '" + pkgname + "'"
    if in_aports:
        ret += " aport"
        if in_apkindexes:
            ret += " and could not find it"
    if in_apkindexes:
        ret += " in any APKINDEX"
    return ret


def recurse(args, pkgnames, arch=None, in_apkindexes=True, in_aports=True,
            strict=False):
    """
    Find all dependencies of the given pkgnames.

    :param in_apkindexes: look through all APKINDEX files (with the specified arch)
    :param in_aports: look through the aports folder
    :param strict: raise RuntimeError, when a dependency can not be found.
    """
    logging.debug("Calculate depends of packages " + str(pkgnames) +
                  ", arch: " + arch)
    logging.verbose("Search in_aports: " + str(in_aports) + ", in_apkindexes: " +
                    str(in_apkindexes))

    # Sanity check
    if not apkindex and not in_aports:
        raise RuntimeError("Set at least one of apkindex or aports to True.")

    todo = list(pkgnames)
    ret = []
    while len(todo):
        # Skip already passed entries
        pkgname = todo.pop(0)
        if pkgname in ret:
            continue

        # Get depends
        logging.verbose("Getting depends of single package: " + pkgname)
        depends = None
        if in_aports:
            aport = pmb.build.find_aport(args, pkgname, False)
            if aport:
                logging.verbose("-> Found aport: " + aport)
                apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
                depends = apkbuild["depends"]
        if depends is None and in_apkindexes:
            logging.verbose("-> Search through APKINDEX files")
            depends = apkindex(args, pkgname, arch)
        if depends is None and strict:
            raise RuntimeError(
                recurse_error_message(
                    pkgname,
                    in_aports,
                    in_apkindexes))

        # Append to todo/ret
        logging.verbose("-> Depends: " + str(depends))
        if depends:
            todo += depends
        ret.append(pkgname)

    return ret
