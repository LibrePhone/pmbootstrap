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


def check_grsec(args):
    """
    Check if the current kernel is based on the grsec patchset, and if
    the chroot_deny_chmod option is enabled. Raise an exception in that
    case, with a link to the issue. Otherwise, do nothing.
    """
    path = "/proc/sys/kernel/grsecurity/chroot_deny_chmod"
    if not os.path.exists(path):
        return

    link = "https://github.com/postmarketOS/pmbootstrap/issues/107"
    raise RuntimeError("You're running a kernel based on the grsec"
                       " patchset. At the moment, pmbootstrap is not"
                       " compatible with grsec or a hardened kernel, sorry!"
                       " To get pmbootstrap working, you will need to switch"
                       " to a vanilla kernel (i.e. non-hardened and without grsec)."
                       " Alternatively, it would be awesome if you want to add"
                       " support for hardened/grsec kernels, please see this for"
                       " more details: <" + link + ">")
