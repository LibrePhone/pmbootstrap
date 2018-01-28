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
import os
import logging
import glob

import pmb.build.other
import pmb.chroot
import pmb.helpers.file
import pmb.helpers.git
import pmb.helpers.run
import pmb.parse.apkindex
import pmb.parse.version


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
        if len(paths) > 2:
            raise RuntimeError("Package " + package + " found in multiple"
                               " aports subfolders. Please put it only in one"
                               " folder.")
        elif len(paths) == 1:
            ret = paths[0]
        else:
            # Search in subpackages
            for path_current in glob.glob(args.aports + "/*/*/APKBUILD"):
                apkbuild = pmb.parse.apkbuild(args, path_current)
                if package in apkbuild["subpackages"]:
                    ret = os.path.dirname(path_current)
                    break

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
        pmb.chroot.root(args, ["rm", "-rf", "/home/pmos/build"],
                        suffix=suffix)

    # Copy aport contents
    pmb.helpers.run.root(args, ["cp", "-r", aport + "/", build])
    pmb.chroot.root(args, ["chown", "-R", "pmos:pmos",
                           "/home/pmos/build"], suffix=suffix)


def is_necessary(args, arch, apkbuild, apkindex_path=None):
    """
    Check if the package has already been built. Compared to abuild's check,
    this check also works for different architectures, and it recognizes
    changed files in an aport folder, even if the pkgver and pkgrel did not
    change.

    :param arch: package target architecture
    :param apkbuild: from pmb.parse.apkbuild()
    :param apkindex_path: override the APKINDEX.tar.gz path
    :returns: boolean
    """
    # Get package name, version, define start of debug message
    package = apkbuild["pkgname"]
    version_new = apkbuild["pkgver"] + "-r" + apkbuild["pkgrel"]
    msg = "Build is necessary for package '" + package + "': "

    # Get old version from APKINDEX
    if apkindex_path:
        index_data = pmb.parse.apkindex.read(
            args, package, apkindex_path, False)
    else:
        index_data = pmb.parse.apkindex.read_any_index(args, package, arch)
    if not index_data:
        logging.debug(msg + "No binary package available")
        return True

    # a) Binary repo has a newer version
    version_old = index_data["version"]
    if pmb.parse.version.compare(version_old, version_new) == 1:
        logging.warning("WARNING: Package '" + package + "' in your aports folder"
                        " has version " + version_new + ", but the binary package"
                        " repositories already have version " + version_old + "!"
                        " See also: <https://postmarketos.org/warning-repo2>")
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
                ["apk", "-q", "index", "--output", "APKINDEX.tar.gz_",
                 "--rewrite-arch", path_arch, "*.apk"],
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
