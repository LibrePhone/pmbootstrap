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


def check_grsec(args):
    """
    Check if the current kernel is based on the grsec patchset, and if
    the chroot_deny_chmod option is enabled. Raise an exception in that
    case, with a link to a wiki page. Otherwise, do nothing.
    """
    path = "/proc/sys/kernel/grsecurity/chroot_deny_chmod"
    if not os.path.exists(path):
        return

    status = pmb.helpers.run.root(
        args, ["cat", path], return_stdout=True).rstrip()
    if status != "0":
        link = "https://github.com/postmarketOS/pmbootstrap/wiki/Troubleshooting:grsec"
        raise RuntimeError("You're running a kernel based on the grsec"
                           " patchset. To get pmbootstrap working, you"
                           " will need to disable some options with"
                           " sysctl: <" + link + ">")
