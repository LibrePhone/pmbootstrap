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
import pmb.config
import fnmatch


def init(args, arch):
    packages = ["gcc-" + arch, "ccache-cross-symlinks"]
    pmb.chroot.apk.install(args, packages)


def native_chroot(args, pkgname):
    for pattern in pmb.config.crosscompile_supported:
        if fnmatch.fnmatch(pkgname, pattern):
            return True
    return False
