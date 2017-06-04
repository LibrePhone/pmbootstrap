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
import pmb.helpers.run


def ismount(folder):
    """
    Ismount() implementation, that works for mount --bind.
    Workaround for: https://bugs.python.org/issue29707
    """
    folder = os.path.abspath(folder)
    with open("/proc/mounts", "r") as handle:
        for line in handle:
            words = line.split()
            if len(words) >= 2 and words[1] == folder:
                return True
            if words[0] == folder:
                return True
    return False


def bind(args, source, destination, create_folders=True):
    """
    Mount --bind a folder and create necessary directory structure.
    """
    if ismount(destination):
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

# Mount a blockdevice


def bind_blockdevice(args, source, destination):
    # Skip existing mountpoint
    if ismount(destination):
        return

    # Create empty file
    if not os.path.exists(destination):
        pmb.helpers.run.root(args, ["touch", destination])

    # Mount
    pmb.helpers.run.root(args, ["mount", "--bind", source,
                                destination])


def umount_all(args, folder):
    """
    Umount all folders, that are mounted inside a given folder.
    """
    folder = os.path.abspath(folder)
    with open("/proc/mounts", "r") as handle:
        for line in handle:
            words = line.split()
            if len(words) < 2 or not words[1].startswith(folder):
                continue
            pmb.helpers.run.root(args, ["umount", words[1]])
            if ismount(words[1]):
                raise RuntimeError("Failed to umount: " + words[1])
