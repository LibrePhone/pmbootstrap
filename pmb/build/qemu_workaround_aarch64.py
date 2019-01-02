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
import pmb.build
import pmb.chroot.apk


def qemu_workaround_aarch64(args, suffix="buildroot_aarch64"):
    """
    Qemu has a bug in aarch64 emulation, that causes abuild-tar to omit files
    from the archives it generates in some cases. We build a patched abuild-tar,
    which avoids the bug.

    https://gitlab.com/postmarketOS/pmbootstrap/issues/546
    """
    pkgname = "abuild-aarch64-qemu-workaround"
    pmb.build.package(args, pkgname, "aarch64", True,
                      skip_init_buildenv=True)
    pmb.chroot.apk.install(args, [pkgname], suffix, False)
