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
import glob
import json
import logging
import os

import pmb.helpers.mount
import pmb.helpers.run
import pmb.chroot


def init(args):
    pmb.helpers.run.root(args, ["modprobe", "loop"])
    loopdevices = [loopdev for loopdev in glob.glob("/dev/loop*") if not os.path.isdir(loopdev)]
    for loopdev in loopdevices:
        pmb.helpers.mount.bind_blockdevice(args, loopdev,
                                           args.work + "/chroot_native/" + loopdev)


def mount(args, img_path):
    """
    :param img_path: Path to the img file inside native chroot.
    """
    logging.debug("(native) mount " + img_path + " (loop)")
    init(args)
    pmb.chroot.root(args, ["losetup", "-f", img_path])


def device_by_back_file(args, back_file):
    """
    Get the /dev/loopX device, that points to a specific image file.
    """

    # Get list from losetup
    losetup_output = pmb.chroot.root(args, ["losetup", "--json",
                                            "--list"], return_stdout=True)
    if not losetup_output:
        return None

    # Find the back_file
    losetup = json.loads(losetup_output)
    for loopdevice in losetup["loopdevices"]:
        if loopdevice["back-file"] == back_file:
            return loopdevice["name"]
    return None


def umount(args, img_path):
    """
    :param img_path: Path to the img file inside native chroot.
    """
    device = device_by_back_file(args, img_path)
    if not device:
        return
    logging.debug("(native) umount " + device)
    pmb.chroot.root(args, ["losetup", "-d", device])
