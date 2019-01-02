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
Functions that work on both pmaports and (binary package) repos. See also:
- pmb/helpers/pmaports.py (work on pmaports)
- pmb/helpers/repo.py (work on binary package repos)
"""

import logging
import copy

import pmb.helpers.pmaports
import pmb.helpers.repo


def get(args, pkgname, arch):
    """ Find a package in pmaports, and as fallback in the APKINDEXes of the
        binary packages.
        :param pkgname: package name (e.g. "hello-world")
        :param arch: preferred architecture of the binary package. When it
                     can't be found for this arch, we'll still look for another
                     arch to see whether the package exists at all. So make
                     sure to check the returned arch against what you wanted
                     with check_arch(). Example: "armhf"
        :returns: data from the parsed APKBUILD or APKINDEX in the following
                  format: {"arch": ["noarch"],
                           "depends": ["busybox-extras", "lddtree", ...],
                           "pkgname": "postmarketos-mkinitfs",
                           "provides": ["mkinitfs=0..1"],
                           "version": "0.0.4-r10"} """
    # Cached result
    cache_key = "pmb.helpers.package.get"
    if (arch in args.cache[cache_key] and
            pkgname in args.cache[cache_key][arch]):
        return args.cache[cache_key][arch][pkgname]

    # Find in pmaports
    ret = None
    pmaport = pmb.helpers.pmaports.get(args, pkgname, False)
    if pmaport:
        ret = {"arch": pmaport["arch"],
               "depends": pmb.build._package.get_depends(args, pmaport),
               "pkgname": pkgname,
               "provides": pmaport["provides"],
               "version": pmaport["pkgver"] + "-r" + pmaport["pkgrel"]}

    # Find in APKINDEX (given arch)
    if not ret:
        pmb.helpers.repo.update(args, arch)
        ret = pmb.parse.apkindex.package(args, pkgname, arch, False)

    # Find in APKINDEX (other arches)
    if not ret:
        pmb.helpers.repo.update(args)
        for arch_i in pmb.config.build_device_architectures:
            if arch_i != arch:
                ret = pmb.parse.apkindex.package(args, pkgname, arch_i, False)
            if ret:
                break

    # Copy ret (it might have references to caches of the APKINDEX or APKBUILDs
    # and we don't want to modify those!)
    if ret:
        ret = copy.deepcopy(ret)

    # Make sure ret["arch"] is a list (APKINDEX code puts a string there)
    if ret and isinstance(ret["arch"], str):
        ret["arch"] = [ret["arch"]]

    # Save to cache and return
    if ret:
        if arch not in args.cache[cache_key]:
            args.cache[cache_key][arch] = {}
        args.cache[cache_key][arch][pkgname] = ret
        return ret

    # Could not find the package
    raise RuntimeError("Package '" + pkgname + "': Could not find aport, and"
                       " could not find this package in any APKINDEX!")


def depends_recurse(args, pkgname, arch):
    """ Recursively resolve all of the package's dependencies.
        :param pkgname: name of the package (e.g. "device-samsung-i9100")
        :param arch: preferred architecture for binary packages
        :returns: a list of pkgname_start and all its dependencies, e.g:
                  ["busybox-static-armhf", "device-samsung-i9100",
                   "linux-samsung-i9100", ...] """
    # Cached result
    cache_key = "pmb.helpers.package.depends_recurse"
    if (arch in args.cache[cache_key] and
            pkgname in args.cache[cache_key][arch]):
        return args.cache[cache_key][arch][pkgname]

    # Build ret (by iterating over the queue)
    queue = [pkgname]
    ret = []
    while len(queue):
        pkgname_queue = queue.pop()
        package = get(args, pkgname_queue, arch)

        # Add its depends to the queue
        for depend in package["depends"]:
            if depend not in ret:
                queue += [depend]
        if pkgname_queue not in ret:
            ret += [pkgname_queue]
    ret.sort()

    # Save to cache and return
    if arch not in args.cache[cache_key]:
        args.cache[cache_key][arch] = {}
    args.cache[cache_key][arch][pkgname] = ret
    return ret


def check_arch(args, pkgname, arch, binary=True):
    """ Can a package be built for a certain architecture, or is there a binary
        package for it?

        :param pkgname: name of the package
        :param arch: architecture to check against
        :param binary: set to False to only look at the pmaports, not at binary
                       packages
        :returns: True when the package can be built, or there is a binary
                  package, False otherwise
    """
    if binary:
        arches = get(args, pkgname, arch)["arch"]
    else:
        arches = pmb.helpers.pmaports.get(args, pkgname)["arch"]

    if "!" + arch in arches:
        return False
    for value in [arch, "all", "noarch"]:
        if value in arches:
            return True
    return False


def check_arch_recurse(args, pkgname, arch):
    """ Recursively check if a package and its dependencies exist (binary repo)
        or can be built (pmaports) for a certain architecture.
        :param pkgname: name of the package
        :param arch: architecture to check against
        :returns: True when all the package's dependencies can be built or
                  exist for the arch in question
    """
    for pkgname_i in depends_recurse(args, pkgname, arch):
        if not check_arch(args, pkgname_i, arch):
            if pkgname_i != pkgname:
                logging.verbose(pkgname_i + ": (indirectly) depends on " +
                                pkgname)
            logging.verbose(pkgname_i + ": can't be built for " + arch)
            return False
    return True
