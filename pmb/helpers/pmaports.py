#!/usr/bin/env python3

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

"""
Functions that work only on pmaports. See also:
- pmb/helpers/repo.py (only work on binary package repos)
- pmb/helpers/package.py (work on both)
"""

import glob
import logging
import os

import pmb.parse


def get_list(args):
    """ :returns: list of all pmaport pkgnames (["hello-world", ...]) """
    ret = []
    for apkbuild in glob.glob(args.aports + "/*/*/APKBUILD"):
        ret.append(os.path.basename(os.path.dirname(apkbuild)))
    ret.sort()
    return ret


def guess_main(args, subpkgname):
    """
    Find the main package by assuming it is a prefix of the subpkgname.
    We do that, because in some APKBUILDs the subpkgname="" variable gets
    filled with a shell loop and the APKBUILD parser in pmbootstrap can't
    parse this right. (Intentionally, we don't want to implement a full shell
    parser.)

    :param subpkgname: subpackage name (e.g. "u-boot-some-device")
    :returns: * full path to the aport, e.g.:
                "/home/user/code/pmbootstrap/aports/main/u-boot"
              * None when we couldn't find a main package
    """
    # Iterate until the cut up subpkgname is gone
    words = subpkgname.split("-")
    while len(words) > 1:
        # Remove one dash-separated word at a time ("a-b-c" -> "a-b")
        words.pop()
        pkgname = "-".join(words)

        # Look in pmaports
        paths = glob.glob(args.aports + "/*/" + pkgname)
        if paths:
            logging.debug(subpkgname + ": guessed to be a subpackage of " +
                          pkgname)
            return paths[0]


def find(args, package, must_exist=True):
    """
    Find the aport path, that provides a certain subpackage.
    If you want the parsed APKBUILD instead, use pmb.helpers.pmaports.get().

    :param must_exist: Raise an exception, when not found
    :returns: the full path to the aport folder
    """
    # Try to get a cached result first (we assume, that the aports don't change
    # in one pmbootstrap call)
    ret = None
    if package in args.cache["find_aport"]:
        ret = args.cache["find_aport"][package]
    else:
        # Sanity check
        if "*" in package:
            raise RuntimeError("Invalid pkgname: " + package)

        # Search in packages
        paths = glob.glob(args.aports + "/*/" + package)
        if len(paths) > 1:
            raise RuntimeError("Package " + package + " found in multiple"
                               " aports subfolders. Please put it only in one"
                               " folder.")
        elif len(paths) == 1:
            ret = paths[0]

        # Search in subpackages and provides
        if not ret:
            for path_current in glob.glob(args.aports + "/*/*/APKBUILD"):
                apkbuild = pmb.parse.apkbuild(args, path_current)
                found = False

                # Subpackages
                for subpackage_i in apkbuild["subpackages"]:
                    if package == subpackage_i.split(":", 1)[0]:
                        found = True
                        break

                # Provides (cut off before equals sign for entries like
                # "mkbootimg=0.0.1")
                if not found:
                    for provides_i in apkbuild["provides"]:
                        if package == provides_i.split("=", 1)[0]:
                            found = True
                            break

                if found:
                    ret = os.path.dirname(path_current)
                    break

        # Guess a main package
        if not ret:
            ret = guess_main(args, package)

    # Crash when necessary
    if ret is None and must_exist:
        raise RuntimeError("Could not find aport for package: " +
                           package)

    # Save result in cache
    args.cache["find_aport"][package] = ret
    return ret


def get(args, pkgname, must_exist=True):
    """ Find and parse an APKBUILD file.
        Run 'pmbootstrap apkbuild_parse hello-world' for a full output example.
        Relevant variables are defined in pmb.config.apkbuild_attributes.

        :param pkgname: the package name to find
        :param must_exist: raise an exception when it can't be found
        :returns: relevant variables from the APKBUILD as dictionary, e.g.:
                  { "pkgname": "hello-world",
                    "arch": ["all"],
                    "pkgrel": "4",
                    "pkgrel": "1",
                    "options": [],
                    ... }
    """
    aport = find(args, pkgname, must_exist)
    if aport:
        return pmb.parse.apkbuild(args, aport + "/APKBUILD")
    return None


def get_repo(args, pkgname, must_exist=True):
    """ Get the repository folder of an aport.

        :pkgname: package name
        :must_exist: raise an exception when it can't be found
        :returns: a string like "main", "device", "cross", ...
                  or None when the aport could not be found """
    aport = find(args, pkgname, must_exist)
    if not aport:
        return None
    return os.path.basename(os.path.dirname(aport))
