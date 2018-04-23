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
import logging
import pmb.chroot
import pmb.chroot.apk
import pmb.parse.apkindex
import pmb.parse.arch


def package_from_aports(args, pkgname_depend):
    """
    :returns: None when there is no aport, or a dict with the keys pkgname,
              depends, version. The version is the combined pkgver and pkgrel.
    """
    # Get the aport
    aport = pmb.build.find_aport(args, pkgname_depend, False)
    if not aport:
        return None

    # Parse its version
    apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
    pkgname = apkbuild["pkgname"]
    version = apkbuild["pkgver"] + "-r" + apkbuild["pkgrel"]

    # Return the dict
    logging.verbose(pkgname_depend + ": provided by: " + pkgname + "-" +
                    version + " in " + aport)
    return {"pkgname": pkgname,
            "depends": apkbuild["depends"],
            "version": version}


def package_provider(args, pkgname, pkgnames_install, suffix="native"):
    """
    :param pkgnames_install: packages to be installed
    :returns: a block from the apkindex: {"pkgname": "...", ...}
              or None (no provider found)
    """
    # Get all providers
    arch = pmb.parse.arch.from_chroot_suffix(args, suffix)
    providers = pmb.parse.apkindex.providers(args, pkgname, arch, False)

    # 0. No provider
    if len(providers) == 0:
        return None

    # 1. Only one provider
    logging.verbose(pkgname + ": provided by: " + ", ".join(providers))
    if len(providers) == 1:
        return list(providers.values())[0]

    # 2. Provider with the same package name
    if pkgname in providers:
        logging.verbose(pkgname + ": choosing package of the same name as"
                        " provider")
        return providers[pkgname]

    # 3. Pick a package that will be installed anyway
    for provider_pkgname, provider in providers.items():
        if provider_pkgname in pkgnames_install:
            logging.verbose(pkgname + ": choosing provider '" +
                            provider_pkgname + "', because it will be"
                            " installed anyway")
            return provider

    # 4. Pick a package that is already installed
    installed = pmb.chroot.apk.installed(args, suffix)
    for provider_pkgname, provider in providers.items():
        if provider_pkgname in installed:
            logging.verbose(pkgname + ": choosing provider '" +
                            provider_pkgname + "', because it is installed in"
                            " the '" + suffix + "' chroot already")
            return provider

    # 5. Pick the first one
    provider_pkgname = list(providers.keys())[0]
    logging.debug(pkgname + " has multiple providers (" +
                  ", ".join(providers) + "), picked: " + provider_pkgname)
    return providers[provider_pkgname]


def package_from_index(args, pkgname_depend, pkgnames_install, package_aport,
                       suffix="native"):
    """
    :returns: None when there is no aport and no binary package, or a dict with
              the keys pkgname, depends, version from either the aport or the
              binary package provider.
    """
    # No binary package
    provider = package_provider(args, pkgname_depend, pkgnames_install, suffix)
    if not provider:
        return package_aport

    # Binary package outdated
    if (package_aport and pmb.parse.version.compare(package_aport["version"],
                                                    provider["version"]) == 1):
        logging.verbose(pkgname_depend + ": binary package is outdated")
        return package_aport

    # Binary up to date (#893: overrides aport, so we have sonames in depends)
    if package_aport:
        logging.verbose(pkgname_depend + ": binary package is"
                        " up to date, using binary dependencies"
                        " instead of the ones from the aport")
    return provider


def recurse(args, pkgnames, suffix="native"):
    """
    Find all dependencies of the given pkgnames.

    :param suffix: the chroot suffix to resolve dependencies for. If a package
                   has multiple providers, we look at the installed packages in
                   the chroot to make a decision (see package_provider()).
    :returns: list of pkgnames: consists of the initial pkgnames plus all
              depends
    """
    logging.debug("(" + suffix + ") calculate depends of " +
                  ", ".join(pkgnames) + " (pmbootstrap -v for details)")

    # Iterate over todo-list until is is empty
    todo = list(pkgnames)
    ret = []
    while len(todo):
        # Skip already passed entries
        pkgname_depend = todo.pop(0)
        if pkgname_depend in ret:
            continue

        # Get depends and pkgname from aports
        pkgnames_install = list(ret) + todo
        package = package_from_aports(args, pkgname_depend)
        package = package_from_index(args, pkgname_depend, pkgnames_install,
                                     package, suffix)

        # Nothing found
        if not package:
            raise RuntimeError("Could not find dependency '" + pkgname_depend +
                               "' in any aports folder or APKINDEX. See:"
                               " <https://postmarketos.org/depends>")

        # Append to todo/ret (unless it is a duplicate)
        pkgname = package["pkgname"]
        if pkgname in ret:
            logging.verbose(pkgname + ": already found")
        else:
            depends = package["depends"]
            logging.verbose(pkgname + ": depends on: " + ",".join(depends))
            if depends:
                todo += depends
            ret.append(pkgname)
    return ret
