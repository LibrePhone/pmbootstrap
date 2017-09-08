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
import fnmatch
import pmb.config
import pmb.chroot.apk
import pmb.parse.arch


def carch(args, apkbuild, carch, strict=False):
    if "noarch" in apkbuild["arch"]:
        if "noarch_arch" in args and args.noarch_arch:
            return args.noarch_arch
        if strict:
            return args.deviceinfo["arch"]
        return args.arch_native
    if carch:
        if "all" not in apkbuild["arch"] and carch not in apkbuild["arch"]:
            raise RuntimeError("Architecture '" + carch + "' is not supported"
                               " for this package. Please add it to the"
                               " 'arch=' line inside the APKBUILD and try"
                               " again: " + apkbuild["pkgname"])
        return carch
    if ("all" in apkbuild["arch"] or
            args.arch_native in apkbuild["arch"]):
        return args.arch_native
    return apkbuild["arch"][0]


def suffix(args, apkbuild, carch):
    if carch == args.arch_native:
        return "native"

    pkgname = apkbuild["pkgname"]
    if pkgname.endswith("-repack"):
        return "native"
    if args.cross:
        for pattern in pmb.config.build_cross_native:
            if fnmatch.fnmatch(pkgname, pattern):
                return "native"

    return "buildroot_" + carch


def crosscompile(args, apkbuild, carch, suffix):
    """
        :returns: None, "native" or "distcc"
    """
    if not args.cross:
        return None
    if apkbuild["pkgname"].endswith("-repack"):
        return None
    if not pmb.parse.arch.cpu_emulation_required(args, carch):
        return None
    if suffix == "native":
        return "native"
    return "distcc"
