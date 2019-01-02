"""
Copyright 2019 Clayton Craft

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
    Get all UIs, for which aports are available with their description.

    :returns: [("none", "No graphical..."), ("weston", "Wayland reference...")]
    """
    ret = [("none", "No graphical environment")]
    for path in sorted(glob.glob(args.aports + "/main/postmarketos-ui-*")):
        apkbuild = pmb.parse.apkbuild(args, path + "/APKBUILD")
        ui = os.path.basename(path).split("-", 2)[2]
        ret.append((ui, apkbuild["pkgdesc"]))
    return ret
