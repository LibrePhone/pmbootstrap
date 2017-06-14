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
import platform
import logging
import fnmatch


def alpine_native():
    machine = platform.machine()
    ret = ""

    if machine == "x86_64":
        ret = "x86_64"
    else:
        raise ValueError("Can not map platform.machine " + machine +
                         " to the right Alpine Linux architecture")

    logging.debug("(native) Alpine architecture: " + ret)
    return ret


def from_chroot_suffix(args, suffix):
    if suffix == "native":
        return args.arch_native
    if suffix == "rootfs_" + args.device:
        return args.deviceinfo["arch"]
    if suffix.startswith("buildroot_"):
        return suffix.split("_", 2)[1]

    raise ValueError("Invalid chroot suffix: " + suffix +
                     " (wrong device chosen in 'init' step?)")


def alpine_to_debian(arch):
    """
    Convert the architecture to the string used in the binfmt info
    (aka. the Debian architecture format).
    """

    mapping = {
        "x86_64": "amd64",
        "armhf": "arm",
        "aarch64": "aarch64",
    }
    for pattern, arch_debian in mapping.items():
        if fnmatch.fnmatch(arch, pattern):
            return arch_debian
    raise ValueError("Can not map Alpine architecture " + arch +
                     " to the right Debian architecture.")


def alpine_to_kernel(arch):
    """
    Convert the architecture to the string used inside the kernel sources.
    You can read the mapping from the linux-vanilla APKBUILD for example.
    """
    mapping = {
        "aarch64*": "arm64",
        "arm*": "arm",
        "ppc*": "powerpc",
        "s390*": "s390"
    }
    for pattern, arch_kernel in mapping.items():
        if fnmatch.fnmatch(arch, pattern):
            return arch_kernel
    return arch


def alpine_to_hostspec(arch):
    """
    See: abuild source code/functions.sh.in: arch_to_hostspec()
    """
    mapping = {
        "aarch64": "aarch64-alpine-linux-musl",
        "armhf": "armv6-alpine-linux-muslgnueabihf",
        "armv7": "armv7-alpine-linux-musleabihf",
        "ppc": "powerpc-alpine-linux-musl",
        "ppc64": "powerpc64-alpine-linux-musl",
        "ppc64le": "powerpc64le-alpine-linux-musl",
        "s390x": "s390x-alpine-linux-musl",
        "x86": "i586-alpine-linux-musl",
        "x86_66": "x86_64-alpine-linux-musl",
    }
    if arch in mapping:
        return mapping[arch]

    raise ValueError("Can not map Alpine architecture " + arch +
                     " to the right hostspec value")
