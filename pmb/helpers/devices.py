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
import pmb.parse


def list(args):
    """
    Get all devices, for which aports are available
    :returns: ["first-device", "second-device", ...]
    """
    ret = []
    for path in glob.glob(args.aports + "/device/device-*"):
        device = os.path.basename(path).split("-", 1)[1]
        ret += [device]
    return ret


def list_apkbuilds(args):
    """
    :returns: { "first-device": {"pkgname": ..., "pkgver": ...}, ... }
    """
    ret = {}
    for device in list(args):
        apkbuild_path = args.aports + "/device-" + device + "/APKBUILD"
        ret[device] = pmb.parse.apkbuild(args, apkbuild_path)
    return ret
