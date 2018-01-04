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
import pmb.config
import pmb.parse
import pmb.helpers.mount


def mount(args, suffix="native"):
    arch = pmb.parse.arch.from_chroot_suffix(args, suffix)

    # Get all mountpoints
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
