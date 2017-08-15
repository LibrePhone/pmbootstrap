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
import glob

import pmb.chroot
import pmb.helpers.run


def zap(args):
    pmb.chroot.shutdown(args)
    patterns = [
        "chroot_native",
        "chroot_buildroot_*",
        "chroot_rootfs_*",
    ]

    # Only ask for removal, if the user specificed the extra '-p' switch.
    # Deleting the packages by accident is really annoying.
    if args.packages:
        patterns += ["packages"]
    if args.http:
        patterns += ["cache_http"]

    for pattern in patterns:
        pattern = os.path.realpath(args.work + "/" + pattern)
        matches = glob.glob(pattern)
        for match in matches:
            if pmb.helpers.cli.confirm(args, "Remove " + match + "?"):
                pmb.helpers.run.root(args, ["rm", "-rf", match])
