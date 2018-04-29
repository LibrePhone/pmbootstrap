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
import pmb.config
import pmb.parse
import pmb.helpers.mount


def create_device_nodes(args, suffix):
    """
    Create device nodes for null, zero, full, random, urandom in the chroot.
    """
    try:
        chroot = args.work + "/chroot_" + suffix

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
        raise RuntimeError("Failed to create device nodes in the '" +
                           suffix + "' chroot.")


def mount_dev_tmpfs(args, suffix="native"):
    """
    Mount tmpfs inside the chroot's dev folder to make sure we can create
    device nodes, even if the filesystem of the work folder does not support
    it.
    """
    # Do nothing when it is already mounted
    dev = args.work + "/chroot_" + suffix + "/dev"
    if pmb.helpers.mount.ismount(dev):
        return

    # Create the $chroot/dev folder and mount tmpfs there
    pmb.helpers.run.root(args, ["mkdir", "-p", dev])
    pmb.helpers.run.root(args, ["mount", "-t", "tmpfs",
                                "-o", "size=1M,noexec,dev",
                                "tmpfs", dev])

    # Create pts, shm folders and device nodes
    pmb.helpers.run.root(args, ["mkdir", "-p", dev + "/pts", dev + "/shm"])
    create_device_nodes(args, suffix)


def mount(args, suffix="native"):
    # Mount tmpfs as the chroot's /dev
    mount_dev_tmpfs(args, suffix)

    # Get all mountpoints
    arch = pmb.parse.arch.from_chroot_suffix(args, suffix)
    mountpoints = {}
    for source, target in pmb.config.chroot_mount_bind.items():
        source = source.replace("$WORK", args.work)
        source = source.replace("$ARCH", arch)
        mountpoints[source] = target

    # Add the pmOS binary repo (in case it is set and points to a local folder)
    mirror = args.mirror_postmarketos
    if os.path.exists(mirror):
        mountpoints[mirror] = "/mnt/postmarketos-mirror"

    # Mount if necessary
    for source, target in mountpoints.items():
        target_full = args.work + "/chroot_" + suffix + target
        pmb.helpers.mount.bind(args, source, target_full)
