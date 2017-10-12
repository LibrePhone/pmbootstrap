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
import json
import pmb.chroot
import pmb.chroot.apk
import pmb.parse.apkindex
import pmb.parse.depends


def generate(args, apk_path, arch, suffix, apkbuild):
    """
    :param apk_path: Path to the .apk file, relative to the packages cache.
    :param arch: Architecture, that the package has been built for.
    :apkbuild: Return from pmb.parse.apkbuild().
    """
    ret = {"pkgname": apkbuild["pkgname"],
           "pkgver": apkbuild["pkgver"],
           "pkgrel": apkbuild["pkgrel"],
           "arch": arch,
           "versions": {}}

    # Add makedepends versions
    installed = pmb.chroot.apk.installed(args, suffix)
    relevant = (apkbuild["makedepends"] + [apkbuild["pkgname"], "abuild",
                                           "build-base"])
    relevant = pmb.parse.depends.recurse(args, relevant, arch, in_aports=False,
                                         strict=True)
    for pkgname in relevant:
        if pkgname == apkbuild["pkgname"]:
            continue
        if pkgname in installed:
            ret["versions"][pkgname] = installed[pkgname]["version"]
    return ret


def write(args, apk_path, arch, suffix, apkbuild):
    """
    Write a .buildinfo.json file for a package, right after building it.
    It stores all information required to rebuild the package, very similar
    to how they do it in Debian (but as JSON file, so it's easier to parse in
    Python): https://wiki.debian.org/ReproducibleBuilds/BuildinfoFiles

    :param apk_path: Path to the .apk file, relative to the packages cache.
    :param arch: Architecture, that the package has been built for.
    :apkbuild: Return from pmb.parse.apkbuild().
    """
    # Write to temp
    if os.path.exists(args.work + "/chroot_native/tmp/buildinfo"):
        pmb.chroot.root(args, ["rm", "/tmp/buildinfo"])
    buildinfo = generate(args, apk_path, arch, suffix, apkbuild)
    with open(args.work + "/chroot_native/tmp/buildinfo", "w") as handle:
        handle.write(json.dumps(buildinfo, indent=4, sort_keys=True) + "\n")

    # Move to packages
    pmb.chroot.root(args, ["chown", "pmos:pmos", "/tmp/buildinfo"])
    pmb.chroot.user(args, ["mv", "/tmp/buildinfo", "/home/pmos/packages/pmos/" +
                           apk_path + ".buildinfo.json"])
