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
import platform
import fnmatch


def alpine_native():
    machine = platform.machine()
    ret = ""

    mapping = {
        "i686": "x86",
        "x86_64": "x86_64",
        "aarch64": "aarch64",
        "armv6l": "armhf",
        "armv7l": "armv7"
    }
    if machine in mapping:
        return mapping[machine]
    raise ValueError("Can not map platform.machine '" + machine + "'"
                     " to the right Alpine Linux architecture")
    return ret


def from_chroot_suffix(args, suffix):
    if suffix == "native":
        return args.arch_native
    if suffix == "rootfs_" + args.device:
        return args.deviceinfo["arch"]
    if suffix.startswith("buildroot_"):
        return suffix.split("_", 1)[1]

    raise ValueError("Invalid chroot suffix: " + suffix +
                     " (wrong device chosen in 'init' step?)")


def alpine_to_qemu(arch):
    """
    Convert the architecture to the string used in the QEMU packaging.
    """

    mapping = {
        "x86": "i386",
        "x86_64": "x86_64",
        "armhf": "arm",
        "armv7": "arm",
        "aarch64": "aarch64",
    }
    for pattern, arch_qemu in mapping.items():
        if fnmatch.fnmatch(arch, pattern):
            return arch_qemu
    raise ValueError("Can not map Alpine architecture '" + arch + "'"
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
        "x86_64": "x86_64-alpine-linux-musl",
    }
    if arch in mapping:
        return mapping[arch]

    raise ValueError("Can not map Alpine architecture '" + arch + "'"
                     " to the right hostspec value")


def cpu_emulation_required(args, arch):
    # Obvious case: host arch is target arch
    if args.arch_native == arch:
        return False

    # Other cases: host arch on the left, target archs on the right
    not_required = {
        "x86_64": ["x86"],
        "aarch64": ["armel", "armhf", "armv7"],
    }
    if args.arch_native in not_required:
        if arch in not_required[args.arch_native]:
            return False

    # No match: then it's required
    return True


def uname_to_qemu(arch):
    """
    Convert the most common architectures returned by 'uname' to those
    used by the QEMU binary
    """
    mapping = {
        "aarch64": "aarch64",
        "arm": "arm",
        "armeb": "arm",
        "armel": "arm",
        "armhf": "arm",
        "armv7l": "arm",
        "x86_64": "x86_64",
        "amd64": "x86_64",
    }
    if arch in mapping:
        return mapping[arch]

    raise ValueError("Can not map host architecture '" + arch + "'"
                     " to the right QEMU value")


def qemu_to_pmos_device(arch):
    """
    Convert the architecture used in the QEMU binary to the aport name in
    postmarketOS defining the device
    """
    mapping = {
        "arm": "qemu-vexpress",
        "aarch64": "qemu-aarch64",
        "x86_64": "qemu-amd64",
    }
    if arch in mapping:
        return mapping[arch]

    raise ValueError("Can not map QEMU value '" + arch + "'"
                     " to the right postmarketOS device")


def qemu_check_device(device, arch):
    """
    Check whether a device has a specific architecture.

    Examples:
        qemu_check_device("qemu-amd64", "x86_64") is True
        qemu_check_device("qemu-vexpress", "armel") is True
        qemu_check_device("qemu-vexpress", "aarch64") is False
    """
    arch_qemu = uname_to_qemu(arch)
    return device == qemu_to_pmos_device(arch_qemu)
