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


def recurse_error_message(pkgname, in_aports, in_apkindexes):
    ret = "Could not find package '" + pkgname + "'"
    if in_aports:
        ret += " in the aports folder"
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
    if not in_apkindexes and not in_aports:
        raise RuntimeError("Set at least one of in_apkindexes or in_aports to"
                           " True.")

    # Iterate over todo-list until is is empty
    todo = list(pkgnames)
    ret = []
    while len(todo):
        # Skip already passed entries
        pkgname_depend = todo.pop(0)
        if pkgname_depend in ret:
            continue

        # Get depends and pkgname from aports
        logging.verbose("Get dependencies of: " + pkgname_depend)
        depends = None
        pkgname = None
        if in_aports:
            aport = pmb.build.find_aport(args, pkgname_depend, False)
            if aport:
                logging.verbose("-> Found aport: " + aport)
                apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
                depends = apkbuild["depends"]
                if pkgname_depend in apkbuild["subpackages"]:
                    pkgname = pkgname_depend
                else:
                    pkgname = apkbuild["pkgname"]

        # Get depends and pkgname from APKINDEX
        if depends is None and in_apkindexes:
            logging.verbose("-> Search through APKINDEX files")
            index_data = pmb.parse.apkindex.read_any_index(args, pkgname_depend,
                                                           arch)
            if index_data:
                depends = index_data["depends"]
                pkgname = index_data["pkgname"]

        # Nothing found
        if pkgname is None and strict:
            raise RuntimeError(
                recurse_error_message(
                    pkgname_depend,
                    in_aports,
                    in_apkindexes))

        # Append to todo/ret (unless it is a duplicate)
        if pkgname != pkgname_depend:
            logging.verbose("-> '" + pkgname_depend + "' is provided by '" +
                            pkgname + "'")
        if pkgname in ret:
            logging.verbose("-> '" + pkgname + "' already found")
        else:
            logging.verbose("-> '" + pkgname + "' depends on: " + str(depends))
            if depends:
                todo += depends
            ret.append(pkgname)

    return ret
