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
import shlex

import pmb.build.other
import pmb.chroot
import pmb.helpers.file
import pmb.helpers.git
import pmb.helpers.run
import pmb.parse.apkindex
import pmb.parse.version


def find_aport_guess_main(args, subpkgname):
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


def find_aport(args, package, must_exist=True):
    """
    Find the aport, that provides a certain subpackage.

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

        # Search in subpackages
        if not ret:
            for path_current in glob.glob(args.aports + "/*/*/APKBUILD"):
                apkbuild = pmb.parse.apkbuild(args, path_current)
                if (package in apkbuild["subpackages"] or
                        package in apkbuild["provides"]):
                    ret = os.path.dirname(path_current)
                    break

        # Guess a main package
        if not ret:
            ret = find_aport_guess_main(args, package)

    # Crash when necessary
    if ret is None and must_exist:
        raise RuntimeError("Could not find aport for package: " +
                           package)

    # Save result in cache
    args.cache["find_aport"][package] = ret
    return ret


def copy_to_buildpath(args, package, suffix="native"):
    # Sanity check
    aport = find_aport(args, package)
    if not os.path.exists(aport + "/APKBUILD"):
        raise ValueError("Path does not contain an APKBUILD file:" +
                         aport)

    # Clean up folder
    build = args.work + "/chroot_" + suffix + "/home/pmos/build"
    if os.path.exists(build):
        pmb.chroot.root(args, ["rm", "-rf", "/home/pmos/build"], suffix)

    # Copy aport contents with resolved symlinks
    pmb.helpers.run.root(args, ["cp", "-rL", aport + "/", build])
    pmb.chroot.root(args, ["chown", "-R", "pmos:pmos",
                           "/home/pmos/build"], suffix)


def is_necessary(args, arch, apkbuild, indexes=None):
    """
    Check if the package has already been built. Compared to abuild's check,
    this check also works for different architectures.

    :param arch: package target architecture
    :param apkbuild: from pmb.parse.apkbuild()
    :param indexes: list of APKINDEX.tar.gz paths
    :returns: boolean
    """
    # Get package name, version, define start of debug message
    package = apkbuild["pkgname"]
    version_new = apkbuild["pkgver"] + "-r" + apkbuild["pkgrel"]
    msg = "Build is necessary for package '" + package + "': "

    # Get old version from APKINDEX
    index_data = pmb.parse.apkindex.package(args, package, arch, False,
                                            indexes)
    if not index_data:
        logging.debug(msg + "No binary package available")
        return True

    # a) Binary repo has a newer version
    version_old = index_data["version"]
    if pmb.parse.version.compare(version_old, version_new) == 1:
        logging.warning("WARNING: package {}: aport version {} is lower than"
                        " {} from the binary repository. {} will be used when"
                        " installing {}. See also:"
                        " <https://postmarketos.org/warning-repo2>"
                        "".format(package, version_new, version_old,
                                  version_old, package))
        return False

    # b) Aports folder has a newer version
    if version_new != version_old:
        logging.debug(msg + "Binary package out of date (binary: " + version_old +
                      ", aport: " + version_new + ")")
        return True

    # Aports and binary repo have the same version.
    return False


def index_repo(args, arch=None):
    """
    Recreate the APKINDEX.tar.gz for a specific repo, and clear the parsing
    cache for that file for the current pmbootstrap session (to prevent
    rebuilding packages twice, in case the rebuild takes less than a second).

    :param arch: when not defined, re-index all repos
    """
    pmb.build.init(args)

    if arch:
        paths = [args.work + "/packages/" + arch]
    else:
        paths = glob.glob(args.work + "/packages/*")

    for path in paths:
        if os.path.isdir(path):
            path_arch = os.path.basename(path)
            path_repo_chroot = "/home/pmos/packages/pmos/" + path_arch
            logging.debug("(native) index " + path_arch + " repository")
            commands = [
                # Wrap the index command with sh so we can use '*.apk'
                ["sh", "-c", "apk -q index --output APKINDEX.tar.gz_"
                 " --rewrite-arch " + shlex.quote(path_arch) + " *.apk"],
                ["abuild-sign", "APKINDEX.tar.gz_"],
                ["mv", "APKINDEX.tar.gz_", "APKINDEX.tar.gz"]
            ]
            for command in commands:
                pmb.chroot.user(args, command, working_dir=path_repo_chroot)
        else:
            logging.debug("NOTE: Can't build index for: " + path)
        pmb.parse.apkindex.clear_cache(args, path + "/APKINDEX.tar.gz")


def configure_abuild(args, suffix, verify=False):
    """
    Set the correct JOBS count in abuild.conf

    :param verify: internally used to test if changing the config has worked.
    """
    path = args.work + "/chroot_" + suffix + "/etc/abuild.conf"
    prefix = "export JOBS="
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.startswith(prefix):
                continue
            if line != (prefix + args.jobs + "\n"):
                if verify:
                    raise RuntimeError("Failed to configure abuild: " + path +
                                       "\nTry to delete the file (or zap the chroot).")
                pmb.chroot.root(args, ["sed", "-i", "-e",
                                       "s/^" + prefix + ".*/" + prefix + args.jobs + "/",
                                       "/etc/abuild.conf"], suffix)
                configure_abuild(args, suffix, True)
            return
    raise RuntimeError("Could not find " + prefix + " line in " + path)


def configure_ccache(args, suffix="native", verify=False):
    """
    Set the maximum ccache size

    :param verify: internally used to test if changing the config has worked.
    """
    # Check if the settings have been set already
    arch = pmb.parse.arch.from_chroot_suffix(args, suffix)
    path = args.work + "/cache_ccache_" + arch + "/ccache.conf"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if line == ("max_size = " + args.ccache_size + "\n"):
                    return
    if verify:
        raise RuntimeError("Failed to configure ccache: " + path + "\nTry to"
                           " delete the file (or zap the chroot).")

    # Set the size and verify
    pmb.chroot.user(args, ["ccache", "--max-size", args.ccache_size],
                    suffix)
    configure_ccache(args, suffix, True)
