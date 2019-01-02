"""
Copyright 2019 Oliver Smith

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
import pmb.helpers.run


def ismount(folder):
    """
    Ismount() implementation, that works for mount --bind.
    Workaround for: https://bugs.python.org/issue29707
    """
    folder = os.path.realpath(os.path.realpath(folder))
    with open("/proc/mounts", "r") as handle:
        for line in handle:
            words = line.split()
            if len(words) >= 2 and words[1] == folder:
                return True
            if words[0] == folder:
                return True
    return False


def bind(args, source, destination, create_folders=True, umount=False):
    """
    Mount --bind a folder and create necessary directory structure.
    :param umount: when destination is already a mount point, umount it first.
    """
    # Check/umount destination
    if ismount(destination):
        if umount:
            umount_all(args, destination)
        else:
            return

    # Check/create folders
    for path in [source, destination]:
        if os.path.exists(path):
            continue
        if create_folders:
            pmb.helpers.run.root(args, ["mkdir", "-p", path])
        else:
            raise RuntimeError("Mount failed, folder does not exist: " +
                               path)

    # Actually mount the folder
    pmb.helpers.run.root(args, ["mount", "--bind", source, destination])

    # Verify, that it has worked
    if not ismount(destination):
        raise RuntimeError("Mount failed: " + source + " -> " + destination)


def bind_blockdevice(args, source, destination):
    """
    Mount a blockdevice with the --bind option, and create the destination
    file, if necessary.
    """
    # Skip existing mountpoint
    if ismount(destination):
        return

    # Create empty file
    if not os.path.exists(destination):
        pmb.helpers.run.root(args, ["touch", destination])

    # Mount
    pmb.helpers.run.root(args, ["mount", "--bind", source,
                                destination])


def umount_all_list(prefix, source="/proc/mounts"):
    """
    Parses `/proc/mounts` for all folders beginning with a prefix.
    :source: can be changed for testcases
    :returns: a list of folders, that need to be umounted
    """
    ret = []
    prefix = os.path.realpath(prefix)
    with open(source, "r") as handle:
        for line in handle:
            words = line.split()
            if len(words) < 2:
                raise RuntimeError("Failed to parse line in " + source + ": " +
                                   line)
            mountpoint = words[1]
            if mountpoint.startswith(prefix):
                # Remove "\040(deleted)" suffix (#545)
                deleted_str = r"\040(deleted)"
                if mountpoint.endswith(deleted_str):
                    mountpoint = mountpoint[:-len(deleted_str)]
                ret.append(mountpoint)
    ret.sort(reverse=True)
    return ret


def umount_all(args, folder):
    """
    Umount all folders, that are mounted inside a given folder.
    """
    for mountpoint in umount_all_list(folder):
        pmb.helpers.run.root(args, ["umount", mountpoint])
        if ismount(mountpoint):
            raise RuntimeError("Failed to umount: " + mountpoint)
