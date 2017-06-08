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
import glob

import pmb.chroot
import pmb.helpers.run
import pmb.parse.apkindex


def find_aport(args, package, must_exist=True):
    """
    Find the aport, that provides a certain subpackage.

    :param must_exist: Raise an exception, when not found
    :returns: the full path to the aport folder
    """
    path = args.aports + "/" + package
    if os.path.exists(path):
        return path

    for path_current in glob.glob(args.aports + "/*/APKBUILD"):
        apkbuild = pmb.parse.apkbuild(path_current)
        if package in apkbuild["subpackages"]:
            return os.path.dirname(path_current)
    if must_exist:
        raise RuntimeError("Could not find aport for package: " +
                           package)
    return None


def copy_to_buildpath(args, package, suffix="native"):
    # Sanity check
    aport = args.aports + "/" + package
    if not os.path.exists(aport + "/APKBUILD"):
        raise ValueError("Path does not contain an APKBUILD file:" +
                         aport)

    # Clean up folder
    build = args.work + "/chroot_" + suffix + "/home/user/build"
    if os.path.exists(build):
        pmb.chroot.root(args, ["rm", "-rf", "/home/user/build"],
                        suffix=suffix)

    # Copy aport contents
    pmb.helpers.run.root(args, ["cp", "-r", aport + "/", build])
    pmb.chroot.root(args, ["chown", "-R", "user:user",
                           "/home/user/build"], suffix=suffix)


def is_necessary(args, suffix, carch, apkbuild):
    """
    Check if the package has already been built (because abuild's check
    only works, if it is the same architecture!)

    :param apkbuild: From pmb.parse.apkbuild()
    :returns: Boolean
    """

    # Get new version from APKBUILD
    package = apkbuild["pkgname"]
    version_new = apkbuild["pkgver"] + "-r" + apkbuild["pkgrel"]

    # Get old version from APKINDEX
    version_old = None
    index_data = pmb.parse.apkindex.read(args, package,
                                         args.work + "/packages/" + carch + "/APKINDEX.tar.gz", False)
    if index_data:
        version_old = index_data["version"]

    if version_new == version_old:
        return False
    if pmb.parse.apkindex.compare_version(version_old,
                                          version_new) == 1:
        logging.warning("WARNING: Package " + package + "-" + version_old +
                        " in your binary repository is higher than the version defined" +
                        " in the APKBUILD. Consider cleaning your package cache" +
                        " (pmbootstrap zap -p) or removing that file and running" +
                        " 'pmbootstrap index'!")
        return False
    return True


def index_repo(args, arch=None):
    """
    :param arch: when not defined, re-index all repos
    """
    pmb.build.init(args)

    if arch:
        paths = [args.work + "/packages/" + arch]
    else:
        paths = glob.glob(args.work + "/packages/*")

    for path in paths:
        path_arch = os.path.basename(path)
        path_repo_chroot = "/home/user/packages/user/" + path_arch
        logging.info("(native) index " + path_arch + " repository")
        commands = [
            ["apk", "index", "--output", "APKINDEX.tar.gz_",
             "--rewrite-arch", path_arch, "*.apk"],
            ["abuild-sign", "APKINDEX.tar.gz_"],
            ["mv", "APKINDEX.tar.gz_", "APKINDEX.tar.gz"]
        ]
        for command in commands:
            pmb.chroot.user(args, command, working_dir=path_repo_chroot)


def symlink_noarch_package(args, arch_apk):
    """
    :param arch_apk: for example: x86_64/mypackage-1.2.3-r0.apk
    """

    # Create the arch folder
    device_arch = args.deviceinfo["arch"]
    device_repo = args.work + "/packages/" + device_arch
    if not os.path.exists(device_repo):
        pmb.chroot.user(args, ["mkdir", "-p", "/home/user/packages/user/" +
                               device_arch])

    # Add symlink, rewrite index
    device_repo_chroot = "/home/user/packages/user/" + device_arch
    pmb.chroot.user(args, ["ln", "-sf", "../" + arch_apk, "."],
                    working_dir=device_repo_chroot)
    index_repo(args, device_arch)


def ccache_stats(args, arch):
    suffix = "native"
    if args.arch:
        suffix = "buildroot_" + arch
    pmb.chroot.user(args, ["ccache", "-s"], suffix, log=False)


# set the correct JOBS count in abuild.conf
def configure_abuild(args, suffix, verify=False):
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
