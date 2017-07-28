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
import shutil

import pmb.build.other
import pmb.chroot
import pmb.helpers.run
import pmb.helpers.file
import pmb.parse.apkindex


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
    build = args.work + "/chroot_" + suffix + "/home/user/build"
    if os.path.exists(build):
        pmb.chroot.root(args, ["rm", "-rf", "/home/user/build"],
                        suffix=suffix)

    # Copy aport contents
    pmb.helpers.run.root(args, ["cp", "-r", aport + "/", build])
    pmb.chroot.root(args, ["chown", "-R", "user:user",
                           "/home/user/build"], suffix=suffix)


def aports_files_out_of_sync_with_git(args, package=None):
    """
    Get a list of files, about which git says, that they have changed in
    comparison to upstream. We need this for the timestamp based rebuild check,
    where it does not only rely on the APKBUILD pkgver and pkgrel, but also on
    the file's last modified date to decide if it needs to be rebuilt. Git sets
    the last modified timestamp to the last checkout date, so we must ignore
    all files, that have not been modified, or else we would trigger rebuilds
    for all packages, from the pmOS binary repository.

    :returns: list of absolute paths to all files not in sync with upstream
    """

    # Filter out a specific package
    if package:
        ret = []
        prefix = os.path.abspath(
            pmb.build.other.find_aport(
                args, package)) + "/"
        for file in aports_files_out_of_sync_with_git(args):
            if file.startswith(prefix):
                ret.append(file)
        return ret

    # Use cached result if possible
    if args.cache["aports_files_out_of_sync_with_git"] is not None:
        return args.cache["aports_files_out_of_sync_with_git"]

    # Get the aport's git repository folder
    git_root = None
    if shutil.which("git"):
        git_root = pmb.helpers.run.user(args, ["git", "rev-parse",
                                               "--show-toplevel"],
                                        working_dir=args.aports,
                                        return_stdout=True,
                                        check=False)
        if git_root:
            git_root = git_root.rstrip()
    ret = []
    if git_root and os.path.exists(git_root):
        # Find tracked files out of sync with upstream
        tracked = pmb.helpers.run.user(args, ["git", "diff", "--name-only", "origin"],
                                       working_dir=git_root, return_stdout=True)

        # Find all untracked files
        untracked = pmb.helpers.run.user(
            args, ["git", "ls-files", "--others", "--exclude-standard"],
            working_dir=git_root, return_stdout=True)

        # Set absolute path, filter out aports files
        aports_absolute = os.path.abspath(args.aports)
        files = tracked.rstrip().split("\n") + untracked.rstrip().split("\n")
        for file in files:
            file = os.path.abspath(git_root + "/" + file)
            if file.startswith(aports_absolute):
                ret.append(file)
    else:
        logging.warning("WARNING: Can not determine, which aport-files have been"
                        " changed from upstream!")
        logging.info("* Aports-folder is not a git repository or git is not"
                     " installed")
        logging.info("* You can turn timestamp-based rebuilds off in"
                     " 'pmbootstrap init'")

    # Save cache
    args.cache["aports_files_out_of_sync_with_git"] = ret
    return ret


def sources_newer_than_binary_package(args, package, index_data):
    path_sources = []
    for file in glob.glob(args.aports + "/*/" + package + "/*"):
        path_sources.append(file)

    lastmod_target = float(index_data["timestamp"])
    return not pmb.helpers.file.is_up_to_date(path_sources,
                                              lastmod_target=lastmod_target)


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
    if pmb.parse.apkindex.compare_version(version_old,
                                          version_new) == 1:
        logging.warning("WARNING: Package '" + package + "' in your aports folder"
                        " has version " + version_new + ", but the binary package"
                        " repositories already have version " + version_old + "!")
        return False

    # b) Aports folder has a newer version
    if version_new != version_old:
        logging.debug(msg + "Binary package out of date (binary: " + version_old +
                      ", aport: " + version_new + ")")
        return True

    # Aports and binary repo have the same version.
    if not args.timestamp_based_rebuild:
        return False

    # c) Same version, source files out of sync with upstream, source
    # files newer than binary package
    files_out_of_sync = aports_files_out_of_sync_with_git(args, package)
    sources_newer = sources_newer_than_binary_package(
        args, package, index_data)
    if len(files_out_of_sync) and sources_newer:
        logging.debug(msg + "Binary package and aport have the same pkgver and"
                      " pkgrel, but there are aport source files out of sync"
                      " with the upstream git repository *and* these source"
                      " files have a more recent 'last modified' timestamp than"
                      " the binary package's build timestamp.")
        return True

    # d) Same version, source files *in sync* with upstream *or* source
    # files *older* than binary package
    else:
        return False


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

    for arch in pmb.config.build_device_architectures:
        # Create the arch folder
        arch_folder = "/home/user/packages/user/" + arch
        arch_folder_outside = args.work + "/packages/" + arch
        if not os.path.exists(arch_folder_outside):
            pmb.chroot.user(args, ["mkdir", "-p", arch_folder])

        # Add symlink, rewrite index
        pmb.chroot.user(args, ["ln", "-sf", "../" + arch_apk, "."],
                        working_dir=arch_folder)
        index_repo(args, arch)


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
