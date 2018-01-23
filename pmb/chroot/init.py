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
import os
import glob
import filecmp

import pmb.chroot
import pmb.chroot.apk_static
import pmb.config
import pmb.helpers.repo
import pmb.helpers.run
import pmb.parse.arch


def copy_resolv_conf(args, suffix="native"):
    """
    Use pythons super fast file compare function (due to caching)
    and copy the /etc/resolv.conf to the chroot, in case it is
    different from the host.
    If the file doesn't exist, create an empty file with 'touch'.
    """
    host = "/etc/resolv.conf"
    chroot = args.work + "/chroot_" + suffix + host
    if os.path.exists(host):
        if not os.path.exists(chroot) or not filecmp.cmp(host, chroot):
            pmb.helpers.run.root(args, ["cp", host, chroot])
    else:
        pmb.helpers.run.root(args, ["touch", chroot])


def create_device_nodes(args, suffix):
    error = ("Failed to create nodes in the '" + suffix + "' chroot. Please"
             " run 'pmbootstrap init' again and put your work folder on a"
             " normal Linux filesystem. (No ntfs, fat, encfs or encfs"
             " encrypted home folder, shared folder etc.)")

    # Folder sturcture
    chroot = args.work + "/chroot_" + suffix
    pmb.helpers.run.root(args, ["mkdir", "-p", chroot + "/dev"])

    try:
        # Create all device nodes as specified in the config
        for dev in pmb.config.chroot_device_nodes:
            path = chroot + "/dev/" + str(dev[4])
            if not os.path.exists(path):
                pmb.helpers.run.root(args, ["mknod",
                                            "-m", str(dev[0]),  # permissions
                                            path,  # name
                                            str(dev[1]),  # type
                                            str(dev[2]),  # major
                                            str(dev[3]),  # minor
                                            ])

        # Verify major and minor numbers of created nodes
        for dev in pmb.config.chroot_device_nodes:
            path = chroot + "/dev/" + str(dev[4])
            stat_result = os.stat(path)
            rdev = stat_result.st_rdev
            assert os.major(rdev) == dev[2], "Wrong major in " + path
            assert os.minor(rdev) == dev[3], "Wrong minor in " + path

        # Verify /dev/zero reading and writing
        path = chroot + "/dev/zero"
        with open(path, "r+b", 0) as handle:
            assert handle.write(bytes([0xff])), "Write failed for " + path
            assert handle.read(1) == bytes([0x00]), "Read failed for " + path

    # On failure: Show filesystem-related error
    except Exception as e:
        logging.info(str(e) + "!")
        raise RuntimeError(error)


def init(args, suffix="native"):
    # When already initialized: just prepare the chroot
    chroot = args.work + "/chroot_" + suffix
    arch = pmb.parse.arch.from_chroot_suffix(args, suffix)
    emulate = pmb.parse.arch.cpu_emulation_required(args, arch)

    pmb.chroot.mount(args, suffix)
    if os.path.islink(chroot + "/bin/sh"):
        if emulate:
            pmb.chroot.binfmt.register(args, arch)
        copy_resolv_conf(args, suffix)
        pmb.chroot.apk.update_repository_list(args, suffix)
        return

    # Require apk-tools-static
    pmb.chroot.apk_static.init(args)

    # Non-native chroot: require qemu-user-static
    if emulate:
        pmb.chroot.apk.install(args, ["qemu-user-static-repack",
                                      "qemu-user-static-repack-binfmt"])
        pmb.chroot.binfmt.register(args, arch)

    logging.info("(" + suffix + ") install alpine-base")

    # Initialize device nodes and cache
    create_device_nodes(args, suffix)
    apk_cache = args.work + "/cache_apk_" + arch
    pmb.helpers.run.root(args, ["ln", "-s", "-f", "/var/cache/apk", chroot +
                                "/etc/apk/cache"])

    # Initialize /etc/apk/keys/, resolv.conf, repositories
    for key in glob.glob(pmb.config.apk_keys_path + "/*.pub"):
        pmb.helpers.run.root(args, ["cp", key, args.work +
                                    "/config_apk_keys/"])
    copy_resolv_conf(args, suffix)
    pmb.chroot.apk.update_repository_list(args, suffix)

    # Non-native chroot: install qemu-user-binary
    if emulate:
        arch_debian = pmb.parse.arch.alpine_to_debian(arch)
        pmb.helpers.run.root(args, ["mkdir", "-p", chroot + "/usr/bin"])
        pmb.helpers.run.root(args, ["cp", args.work +
                                    "/chroot_native/usr/bin/qemu-" + arch_debian + "-static",
                                    chroot + "/usr/bin/qemu-" + arch_debian + "-static"])

    # Install alpine-base (no clean exit for non-native chroot!)
    pmb.chroot.apk_static.run(args, ["--root", chroot,
                                     "--cache-dir", apk_cache, "--initdb", "--arch", arch,
                                     "add", "alpine-base"])

    # Building chroots: create "pmos" user, add symlinks to /home/pmos
    if not suffix.startswith("rootfs_"):
        pmb.chroot.root(args, ["adduser", "-D", "pmos", "-u",
                        pmb.config.chroot_uid_user], suffix, auto_init=False)

        # Create the links (with subfolders if necessary)
        for target, link_name in pmb.config.chroot_home_symlinks.items():
            link_dir = os.path.dirname(link_name)
            if not os.path.exists(chroot + link_dir):
                pmb.chroot.user(args, ["mkdir", "-p", link_dir], suffix)
            pmb.chroot.user(args, ["ln", "-s", target, link_name], suffix)
            pmb.chroot.root(args, ["chown", "pmos:pmos", target],
                            suffix)
