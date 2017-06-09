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


def package_split(package):
    """
    Split a full package name (as returned by `apk info -vv` and as found as
    apk file name) into its components.
    :param package: Example: "heimdall-1.4.2-r1"
    """
    split = package.split("-")
    pkgrel = split[-1][1:]
    pkgver = split[-2]
    version = "-" + pkgver + "-r" + pkgrel
    pkgname = package[:-1 * len(version)]
    return {"pkgname": pkgname,
            "pkgrel": pkgrel,
            "pkgver": pkgver,
            "package": package}
