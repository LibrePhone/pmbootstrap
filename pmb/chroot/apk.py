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
import os
import pmb.chroot
import pmb.parse.apkindex


def install(args, packages, suffix="native", build=True):
    """
    :param build: automatically build the package, when it does not exist yet
        and it is inside the pm-aports folder. Checking this is expensive - if
        you know, that all packages are provides by upstream repos, set this to
        False!
    """
    # Initialize chroot
    pmb.chroot.init(args, suffix)

    # Filter already installed packages
    packages_installed = installed(args, suffix)
    packages_todo = []
    for package in packages:
        if package not in packages_installed:
            packages_todo.append(package)
    if not len(packages_todo):
        return

    # Build packages if necessary
    arch = pmb.parse.arch.from_chroot_suffix(args, suffix)
    if build:
        for package in packages_todo:
            pmb.build.package(args, package, arch)

    # Sanitize packages: don't allow '--allow-untrusted' and other options
    # to be passed to apk!
    for package in packages_todo:
        if package.startswith("-"):
            raise ValueError("Invalid package name: " + package)

    # Install everything
    logging.info("(" + suffix + ") install " + " ".join(packages_todo))
    pmb.chroot.root(args, ["apk", "--no-progress", "add"] + packages_todo,
                    suffix)


def upgrade(args, suffix="native", update_index=True):
    """
    Upgrade all packages installed in a chroot
    """
    pmb.chroot.init(args, suffix)
    if update_index:
        pmb.chroot.root(args, ["apk", "update"], suffix)

        # -a: also update previously downgraded (and therefore pinned) packages
    pmb.chroot.root(args, ["apk", "upgrade", "-a"], suffix)


def installed(args, suffix="native"):
    """
    Get all explicitly installed packages
    """
    world = args.work + "/chroot_" + suffix + "/etc/apk/world"
    if not os.path.exists(world):
        return []
    with open(world, encoding="utf-8") as handle:
        return handle.read().splitlines()
