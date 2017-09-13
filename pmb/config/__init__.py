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
import multiprocessing
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
version = "0.2.0"
pmb_src = os.path.normpath(os.path.realpath(__file__) + "/../../..")
apk_keys_path = pmb_src + "/keys"

# Update this frequently to prevent a MITM attack with an outdated version
# (which may contain a vulnerable apk/libressl, and allows an attacker to
# exploit the system!)
apk_tools_static_min_version = "2.7.2-r0"

# Config file/commandline default values
# $WORK gets replaced with the actual value for args.work (which may be
# overriden on the commandline)
defaults = {
    "alpine_version": "edge",  # alternatively: latest-stable
    "aports": os.path.normpath(pmb_src + "/aports"),
    "config": os.path.expanduser("~") + "/.config/pmbootstrap.cfg",
    "device": "samsung-i9100",
    "extra_packages": "none",
    "jobs": str(multiprocessing.cpu_count() + 1),
    "timestamp_based_rebuild": True,
    "log": "$WORK/log.txt",
    "mirror_alpine": "https://nl.alpinelinux.org/alpine/",
    "mirror_postmarketos": "",
    "work": os.path.expanduser("~") + "/.local/var/pmbootstrap",
    "port_distccd": "33632",
    "ui": "weston",
    "keymap": "",

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

# Officially supported target architectures for postmarketOS. Only
# specify architectures supported by Alpine here. When creating a noarch
# package, symlinks for all architectures get created - so only specify
# architectures, where we really have device-* packages for.
build_device_architectures = ["armhf", "aarch64"]

# Packages, that will be installed in a chroot before it builds packages
# for the first time
build_packages = ["abuild", "build-base", "ccache"]

# fnmatch for supported pkgnames, that can be directly compiled inside
# the native chroot and a cross-compiler, without using distcc
build_cross_native = ["linux-*"]


#
# PARSE
#

# Variables in APKBUILD files, that get parsed
apkbuild_attributes = {
    "arch": {"array": True},
    "depends": {"array": True},
    "depends_dev": {"array": True},
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

    # mesa
    "_llvmver": {"array": False},
}

# Variables from deviceinfo. Reference: <https://postmarketos.org/deviceinfo>
deviceinfo_attributes = [
    # device
    "format_version",
    "name",
    "manufacturer",
    "date",
    "keyboard",
    "nonfree",
    "dtb",
    "modules_initfs",
    "external_disk",
    "external_disk_install",
    "flash_methods",
    "arch",

    # flash
    "generate_bootimg",
    "generate_legacy_uboot_initfs",
    "flash_heimdall_partition_kernel",
    "flash_heimdall_partition_initfs",
    "flash_heimdall_partition_system",
    "flash_offset_base",
    "flash_offset_kernel",
    "flash_offset_ramdisk",
    "flash_offset_second",
    "flash_offset_tags",
    "flash_pagesize",
    "flash_sparse",
    "kernel_cmdline",

    # weston
    "weston_pixman_type",

    # keymaps
    "keymaps",
]

#
# INITFS
#
initfs_hook_prefix = "postmarketos-mkinitfs-hook-"
default_ip = "172.16.42.1"


#
# INSTALL
#

# Packages, that will be installed inside the native chroot to perform
# the installation to the device.
# util-linux: losetup, fallocate
install_native_packages = ["cryptsetup", "util-linux", "e2fsprogs", "parted"]
install_device_packages = [

    # postmarketos
    "postmarketos-base",

    # other
    "ttf-droid"
]


#
# FLASH
#

# These folders will be mounted at the same location into the native
# chroot, before the flash programs get started.
flash_mount_bind = [
    "/sys/bus/usb/devices/",
    "/sys/dev/",
    "/sys/devices/",
    "/dev/bus/usb/"
]

"""
Flasher abstraction. Allowed variables:

$BOOT: Path to the /boot partition
$FLAVOR: Kernel flavor
$IMAGE: Path to the system partition image
$PARTITION_SYSTEM: Partition to flash the system image

Fastboot specific: $KERNEL_CMDLINE
Heimdall specific: $PARTITION_KERNEL, $PARTITION_INITFS
"""
flashers = {
    "fastboot": {
        "depends": ["android-tools"],
        "actions":
                {
                    "list_devices": [["fastboot", "devices", "-l"]],
                    "flash_system": [["fastboot", "flash", "$PARTITION_SYSTEM", "$IMAGE"]],
                    "flash_kernel": [["fastboot", "flash", "boot", "$BOOT/boot.img-$FLAVOR"]],
                    "boot": [["fastboot", "-c", "$KERNEL_CMDLINE", "boot", "$BOOT/boot.img-$FLAVOR"]],

        },
    },
    # Some Samsung devices need the initramfs to be baked into the kernel (e.g.
    # i9070, i9100). We want the initramfs to be generated after the kernel was
    # built, so we put the real initramfs on another partition (e.g. RECOVERY)
    # and load it from the initramfs in the kernel. This method is called
    # "isorec" (isolated recovery), a term coined by Lanchon.
    "heimdall-isorec": {
        "depends": ["heimdall"],
        "actions":
        {
            "list_devices": [["heimdall", "detect"]],
            "flash_system": [
                ["heimdall_wait_for_device.sh"],
                ["heimdall", "flash", "--$PARTITION_SYSTEM", "$IMAGE"]],
            "flash_kernel": [["heimdall_flash_kernel.sh",
                              "$BOOT/initramfs-$FLAVOR", "$PARTITION_INITFS",
                              "$BOOT/vmlinuz-$FLAVOR", "$PARTITION_KERNEL"]]
        },
    },
    # Some Samsung devices need a 'boot.img' file, just like the one generated
    # fastboot compatible devices. Example: s7562, n7100
    "heimdall-bootimg": {
        "depends": ["heimdall"],
        "actions":
        {
            "list_devices": [["heimdall", "detect"]],
            "flash_system": [
                ["heimdall_wait_for_device.sh"],
                ["heimdall", "flash", "--$PARTITION_SYSTEM", "$IMAGE"]],
            "flash_kernel": [
                ["heimdall_wait_for_device.sh"],
                ["heimdall", "flash", "--$PARTITION_KERNEL", "$BOOT/boot.img-$FLAVOR"]],
        },
    },
    "adb": {
            "depends": ["android-tools"],
            "actions":
            {
                "list_devices": [["adb", "-P", "5038", "devices"]],
                "sideload": [["echo", "< wait for any device >"],
                             ["adb", "-P", "5038", "wait-for-usb-sideload"],
                             ["adb", "-P", "5038", "sideload",
                              "$RECOVERY_ZIP"]],
            }
    },
}

#
# GIT
#
git_repos = {
    "aports_upstream": "https://github.com/alpinelinux/aports",
    "apk-tools": "https://github.com/alpinelinux/apk-tools",
}
