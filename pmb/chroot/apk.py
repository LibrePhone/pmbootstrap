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
import os
import logging
import pmb.chroot
import pmb.config
import pmb.parse.apkindex
import pmb.parse.arch
import pmb.parse.depends


def check_min_version(args, suffix="native"):
    """
    Check the minimum apk version, before running it the first time in the
    current session (lifetime of one pmbootstrap call).
    """

    # Skip if we already did this
    if suffix in args.cache["apk_min_version_checked"]:
        return

    # Skip if apk is not installed yet
    if not os.path.exists(args.work + "/chroot_" + suffix + "/sbin/apk"):
        logging.debug("NOTE: Skipped apk version check for chroot '" + suffix +
                      "', because it is not installed yet!")
        return

    # Compare
    version_installed = installed(args, suffix)["apk-tools"]["version"]
    version_min = pmb.config.apk_tools_static_min_version
    if pmb.parse.apkindex.compare_version(
            version_installed, version_min) == -1:
        raise RuntimeError("You have an outdated version of the 'apk' package"
                           " manager installed (your version: " + version_installed +
                           ", expected at least: " + version_min + "). Delete"
                           " your http cache and zap all chroots, then try again:"
                           " 'pmbootstrap zap -hc'")

    # Mark this suffix as checked
    args.cache["apk_min_version_checked"].append(suffix)


def install_is_necessary(args, build, arch, package, packages_installed):
    """
    This function optionally builds an out of date package, and checks if the
    version installed inside a chroot is up to date.
    :param build: Set to true to build the package, if the binary packages are
                  out of date, and it is in the aports folder.
    :param packages_installed: Return value from installed().
    :returns: True if the package needs to be installed/updated, False otherwise.
    """
    # Build package
    if build:
        pmb.build.package(args, package, arch)

    # No further checks when not installed
    if package not in packages_installed:
        return True

    # Compare the installed version vs. the version in the repos
    data_installed = packages_installed[package]
    data_repo = pmb.parse.apkindex.read_any_index(args, package, arch)
    compare = pmb.parse.apkindex.compare_version(data_installed["version"],
                                                 data_repo["version"])
    # a) Installed newer (should not happen normally)
    if compare == 1:
        logging.info("WARNING: " + arch + " package '" + package +
                     "' installed version " + data_installed["version"] +
                     " is newer, than the version in the repositories: " +
                     data_repo["version"])
        return False

    # b) Repo newer
    elif compare == -1:
        return True

    # c) Same version, look at last modified
    elif compare == 0:
        time_installed = float(data_installed["timestamp"])
        time_repo = float(data_repo["timestamp"])
        return time_repo > time_installed


def replace_aports_packages_with_path(args, packages, suffix, arch):
    """
    apk will only re-install packages with the same pkgname, pkgver and pkgrel,
    when you give it the absolute path to the package. This function replaces
    all packages, that were built locally, with the absolute path to the package.
    """
    ret = []
    for package in packages:
        aport = pmb.build.find_aport(args, package, False)
        if aport:
            apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
            apk_path = ("/home/user/packages/user/" + arch + "/" +
                        package + "-" + apkbuild["pkgver"] + "-r" +
                        apkbuild["pkgrel"] + ".apk")
            if os.path.exists(args.work + "/chroot_" + suffix + apk_path):
                package = apk_path
        ret.append(package)
    return ret


def install(args, packages, suffix="native", build=True):
    """
    :param build: automatically build the package, when it does not exist yet
                  or needs to be updated, and it is inside the pm-aports
                  folder. Checking this is expensive - if you know, that all
                  packages are provides by upstream repos, set this to False!
    """
    # Initialize chroot
    check_min_version(args, suffix)
    pmb.chroot.init(args, suffix)

    # Add depends to packages
    arch = pmb.parse.arch.from_chroot_suffix(args, suffix)
    packages_with_depends = pmb.parse.depends.recurse(args, packages, arch,
                                                      strict=True)

    # Filter out up-to-date packages
    packages_installed = installed(args, suffix)
    packages_todo = []
    for package in packages_with_depends:
        if install_is_necessary(
                args, build, arch, package, packages_installed):
            packages_todo.append(package)
    if not len(packages_todo):
        return

    # Sanitize packages: don't allow '--allow-untrusted' and other options
    # to be passed to apk!
    for package in packages_todo:
        if package.startswith("-"):
            raise ValueError("Invalid package name: " + package)

    # Readable install message without dependencies
    message = "(" + suffix + ") install"
    for pkgname in packages:
        if pkgname not in packages_installed:
            message += " " + pkgname
    logging.info(message)

    # Install/update everything
    packages_todo = replace_aports_packages_with_path(args, packages_todo,
                                                      suffix, arch)
    pmb.chroot.root(args, ["apk", "--no-progress", "add", "-u"] + packages_todo,
                    suffix)


def upgrade(args, suffix="native", update_index=True):
    """
    Upgrade all packages installed in a chroot
    """
    # Prepare apk and update index
    check_min_version(args, suffix)
    pmb.chroot.init(args, suffix)
    if update_index:
        pmb.chroot.root(args, ["apk", "update"], suffix)

    # Rebuild and upgrade out-of-date packages
    packages = installed(args, suffix).keys()
    install(args, packages, suffix)


def installed(args, suffix="native"):
    """
    Read the list of installed packages (which has almost the same format, as
    an APKINDEX, but with more keys).

    :returns: a dictionary with the following structure:
              { "postmarketos-mkinitfs":
                {
                  "pkgname": "postmarketos-mkinitfs"
                  "version": "0.0.4-r10",
                  "depends": ["busybox-extras", "lddtree", ...],
                  "provides": ["mkinitfs=0.0.1"]
                }, ...
              }
    """
    path = args.work + "/chroot_" + suffix + "/lib/apk/db/installed"
    if not os.path.exists(path):
        return {}
    return pmb.parse.apkindex.parse(args, path)
