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

#
# Exported functions
#
from pmb.config.init import init
from pmb.config.load import load
from pmb.config.save import save


#
# Exported variables (internal configuration)
#
version = "0.1.0"
pmb_src = os.path.normpath(os.path.realpath(__file__) + "/../../..")
apk_keys_path = pmb_src + "/keys"

# Update this frequently to prevent a MITM attack with an outdated version
# (which may contain a vulnerable apk/libressl, and allows an attacker to
# exploit the system!)
apk_tools_static_min_version = "2.7.1-r0"

# Config file/commandline default values
# $WORK gets replaced with the actual value for args.work (which may be
# overriden on the commandline)
defaults = {
    "alpine_version": "edge",  # alternatively: latest-stable
    "aports": os.path.normpath(pmb_src + "/aports"),
    "config": os.path.expanduser("~") + "/.config/pmbootstrap.cfg",
    "device": "samsung-i9100",
    "log": "$WORK/log.txt",
    "mirror_alpine": "https://nl.alpinelinux.org/alpine/",
    "work": os.path.expanduser("~") + "/.local/var/pmbootstrap",
    "port_distccd": "33632",

    # aes-xts-plain64 would be better, but this is not supported on LineageOS
    # kernel configs
    "cipher": "aes-cbc-plain64"
}

#
# CHROOT
#

# Usually the ID for the first user created is 1000. However, we want
# pmbootstrap to work even if the 'user' account inside the chroots has
# another UID, so we force it to be different.
chroot_uid_user = "12345"

# The PATH variable used inside all chroots
chroot_path = ":".join([
    "/usr/lib/ccache/bin",
    "/usr/local/sbin",
    "/usr/local/bin",
    "/usr/sbin:/usr/bin",
    "/sbin",
    "/bin"
])

# The PATH variable used on the host, to find the "chroot" and "sh"
# executables. As pmbootstrap runs as user, not as root, the location
# for the chroot executable may not be in the PATH (Debian).
chroot_host_path = os.environ["PATH"] + ":/usr/sbin/"

# Folders, that get mounted inside the chroot
# $WORK gets replaced with args.work
# $ARCH gets replaced with the chroot architecture (eg. x86_64, armhf)
chroot_mount_bind = {
    "/proc": "/proc",
    "$WORK/cache_apk_$ARCH": "/var/cache/apk",
    "$WORK/cache_ccache_$ARCH": "/home/user/.ccache",
    "$WORK/cache_distfiles": "/var/cache/distfiles",
    "$WORK/cache_git": "/home/user/git",
    "$WORK/config_abuild": "/home/user/.abuild",
    "$WORK/config_apk_keys": "/etc/apk/keys",
    "$WORK/packages": "/home/user/packages/user",
}

# The package alpine-base only creates some device nodes. Specify here, which
# additional nodes will get created during initialization of the chroot.
# Syntax for each entry: [permissions, type, major, minor, name]
chroot_device_nodes = [
    [666, "c", 1, 5, "zero"],
    [666, "c", 1, 7, "full"],
    [644, "c", 1, 8, "random"],
    [644, "c", 1, 9, "urandom"],
]


#
# BUILD
#

# Packages, that will be installed in a chroot before it builds packages
# for the first time
build_packages = ["abuild", "build-base", "ccache"]

# fnmatch for supported pkgnames, that can be directly compiled inside
# the native chroot and a cross-compiler, without using distcc
build_cross_native = ["linux-*"]

# Variables in APKBUILD files, that get parsed
apkbuild_attributes = {
    "arch": {"array": True},
    "depends": {"array": True},
    "makedepends": {"array": True},
    "options": {"array": True},
    "pkgname": {"array": False},
    "pkgrel": {"array": False},
    "pkgver": {"array": False},
    "subpackages": {"array": True},

    # cross-compilers
    "makedepends_build": {"array": True},
    "makedepends_host": {"array": True},

    # kernels
    "_flavor": {"array": False},
    "_device": {"array": False},
    "_kernver": {"array": False},
    "_pmb_build_in_native_chroot": {"array": False},

    # mesa
    "_llvmver": {"array": False},
}

#
# INSTALL
#

# Packages, that will be installed inside the native chroot to perform
# the installation to the device.
# util-linux: losetup, fallocate
install_native_packages = ["cryptsetup", "util-linux", "e2fsprogs", "parted"]
install_device_packages = [

    # postmarketos
    "postmarketos-base", "postmarketos-demos",

    # weston
    "weston", "weston-shell-desktop", "weston-backend-fbdev", "weston-backend-drm",
    "weston-backend-x11", "weston-clients", "weston-terminal",
    "weston-xwayland", "xorg-server-xwayland",

    # other
    "ttf-droid"
]
install_size_image = "835M"
install_size_boot = "100M"


#
# FLASH
#

# These folders will be mounted at the same location into the native
# chroot, before the flash programs get started.
flash_mount_bind = [
    "/sys/bus/usb/devices/",
    "/sys/devices/",
    "/dev/bus/usb/"
]

# Allowed variables:
# $KERNEL, $RAMDISK, $IMAGE (system partition image), $BOOTPARAM
flashers = {
    "fastboot": {
        "depends": ["android-tools"],
        "actions":
                {
                    "list_devices": [["fastboot", "devices", "-l"]],
            "flash_system": [["fastboot", "flash", "system", "$IMAGE"]],
            "flash_kernel": [["fastboot",
                              "--base", "$OFFSET_BASE",
                              "--kernel-offset", "$OFFSET_KERNEL",
                              "--ramdisk-offset", "$OFFSET_RAMDISK",
                              "--tags-offset", "$OFFSET_TAGS",
                              "--page-size", "$PAGE_SIZE",
                              "flash:raw", "$KERNEL", "$RAMDISK"]],
            "boot": [["fastboot",
                      "--base", "$OFFSET_BASE",
                      "--kernel-offset", "$OFFSET_KERNEL",
                      "--ramdisk-offset", "$OFFSET_RAMDISK",
                      "--tags-offset", "$OFFSET_TAGS",
                      "--page-size", "$PAGE_SIZE",
                      "boot", "$KERNEL", "$RAMDISK"]],
        }
    },
    "heimdall": {
        "depends": ["heimdall"],
        "actions":
                {
                    "list_devices": [["heimdall", "detect"]],
            "flash_system": [
                        ["heimdall_wait_for_device.sh"],
                        ["heimdall", "flash", "--SYSTEM", "$IMAGE"]],
            "flash_kernel": [["heimdall_flash_kernel.sh", "$RAMDISK", "$KERNEL"]]
        },
    },
}

#
# GIT
#
git_repos = {
    "aports_upstream": "https://github.com/alpinelinux/aports",
    "apk-tools": "https://github.com/alpinelinux/apk-tools",
}
