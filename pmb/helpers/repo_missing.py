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

import pmb.build
import pmb.helpers.package
import pmb.helpers.pmaports


def filter_missing_packages(args, arch, pkgnames):
    """ Create a subset of pkgnames with missing or outdated binary packages.

        :param arch: architecture (e.g. "armhf")
        :param pkgnames: list of package names (e.g. ["hello-world", "test12"])
        :returns: subset of pkgnames (e.g. ["hello-world"]) """
    ret = []
    for pkgname in pkgnames:
        binary = pmb.parse.apkindex.package(args, pkgname, arch, False)
        must_exist = False if binary else True
        pmaport = pmb.helpers.pmaports.get(args, pkgname, must_exist)
        if pmaport and pmb.build.is_necessary(args, arch, pmaport):
            ret.append(pkgname)
    return ret


def filter_aport_packages(args, arch, pkgnames):
    """ Create a subset of pkgnames where each one has an aport.

        :param arch: architecture (e.g. "armhf")
        :param pkgnames: list of package names (e.g. ["hello-world", "test12"])
        :returns: subset of pkgnames (e.g. ["hello-world"]) """
    ret = []
    for pkgname in pkgnames:
        if pmb.helpers.pmaports.find(args, pkgname, False):
            ret += [pkgname]
    return ret


def filter_arch_packages(args, arch, pkgnames):
    """ Create a subset of pkgnames with packages removed that can not be
        built for a certain arch. The check is recursive, if one of the
        dependencies of a package can not be built for the arch in question,
        then it will not be in the final list either.

        :param arch: architecture (e.g. "armhf")
        :param pkgnames: list of package names (e.g. ["hello-world", "test12"])
        :returns: subset of pkgnames (e.g. ["hello-world"]) """
    ret = []
    for pkgname in pkgnames:
        if pmb.helpers.package.check_arch_recurse(args, pkgname, arch):
            ret += [pkgname]
    return ret


def get_relevant_packages(args, arch, pkgname=None, built=False):
    """ Get all packages that can be built for the architecture in question.

        :param arch: architecture (e.g. "armhf")
        :param pkgname: only look at a specific package (and its dependencies)
        :param built: include packages that have already been built
        :returns: an alphabetically sorted list of pkgnames, e.g.:
                  ["devicepkg-dev", "hello-world", "osk-sdl"] """
    if pkgname:
        if not pmb.helpers.package.check_arch_recurse(args, pkgname, arch):
            raise RuntimeError(pkgname + " can't be built for " + arch + "."
                               " Either itself or one if its dependencies is"
                               " not available for that architecture. Run with"
                               " -v for details.")
        ret = pmb.helpers.package.depends_recurse(args, pkgname, arch)
    else:
        ret = pmb.helpers.pmaports.get_list(args)
        ret = filter_arch_packages(args, arch, ret)
    if built:
        ret = filter_aport_packages(args, arch, ret)
        if not len(ret):
            logging.info("NOTE: no aport found for any package in the"
                         " dependency tree, it seems they are all provided by"
                         " upstream (Alpine).")
    else:
        ret = filter_missing_packages(args, arch, ret)
        if not len(ret):
            logging.info("NOTE: all relevant packages are up to date, use"
                         " --built to include the ones that have already been"
                         " built.")

    # Sort alphabetically (to get a deterministic build order)
    ret.sort()
    return ret


def generate_output_format(args, arch, pkgnames):
    """ Generate the detailed output format.
        :param arch: architecture
        :param pkgnames: list of package names that should be in the output,
                         e.g.: ["hello-world", "pkg-depending-on-hello-world"]
        :returns: a list like the following:
                  [{"pkgname": "hello-world",
                    "repo": "main",
                    "version": "1-r4",
                    "depends": []},
                   {"pkgname": "pkg-depending-on-hello-world",
                    "version": "0.5-r0",
                    "repo": "main",
                    "depends": ["hello-world"]}] """
    ret = []
    for pkgname in pkgnames:
        entry = pmb.helpers.package.get(args, pkgname, arch, True)
        ret += [{"pkgname": entry["pkgname"],
                 "repo": pmb.helpers.pmaports.get_repo(args, pkgname),
                 "version": entry["version"],
                 "depends": entry["depends"]}]
    return ret


def generate(args, arch, overview, pkgname=None, built=False):
    """ Get packages that need to be built, with all their dependencies.

        :param arch: architecture (e.g. "armhf")
        :param pkgname: only look at a specific package
        :param built: include packages that have already been built
        :returns: a list like the following:
                  [{"pkgname": "hello-world",
                    "repo": "main",
                    "version": "1-r4"},
                   {"pkgname": "package-depending-on-hello-world",
                    "version": "0.5-r0",
                    "repo": "main"}]
    """
    # Log message
    packages_str = pkgname if pkgname else "all packages"
    logging.info("Calculate packages that need to be built ({}, {}) - this may"
                 " take some time".format(packages_str, arch))

    # Order relevant packages
    ret = get_relevant_packages(args, arch, pkgname, built)

    # Output format
    if overview:
        return ret
    return generate_output_format(args, arch, ret)
