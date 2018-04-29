"""
Copyright 2018 Oliver Smith

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
from pmb.config.load import load
from pmb.config.save import save
from pmb.config.merge_with_args import merge_with_args


#
# Exported variables (internal configuration)
#
version = "0.7.0"
pmb_src = os.path.normpath(os.path.realpath(__file__) + "/../../..")
apk_keys_path = pmb_src + "/keys"

# Update this frequently to prevent a MITM attack with an outdated version
# (which may contain a vulnerable apk/libressl, and allows an attacker to
# exploit the system!)
apk_tools_static_min_version = "2.9.0-r0"

# Version of the work folder (as asked during 'pmbootstrap init'). Increase
# this number, whenever migration is required and provide the migration code,
# see migrate_work_folder()).
work_version = 2

# Only save keys to the config file, which we ask for in 'pmbootstrap init'.
config_keys = ["ccache_size", "device", "extra_packages", "hostname", "jobs",
               "kernel", "keymap", "nonfree_firmware", "nonfree_userland",
               "qemu_native_mesa_driver", "ssh_keys", "timezone", "ui", "user",
               "work"]

# Config file/commandline default values
# $WORK gets replaced with the actual value for args.work (which may be
# overriden on the commandline)
defaults = {
    "alpine_version": "edge",  # alternatively: latest-stable
    "aports": os.path.normpath(pmb_src + "/aports"),
    "ccache_size": "5G",
    # aes-xts-plain64 would be better, but this is not supported on LineageOS
    # kernel configs
    "cipher": "aes-cbc-plain64",
    "config": os.path.expanduser("~") + "/.config/pmbootstrap.cfg",
    "device": "samsung-i9100",
    "extra_packages": "none",
    "hostname": "",
    # A higher value is typically desired, but this can lead to VERY long open
    # times on slower devices due to host systems being MUCH faster than the
    # target device: <https://github.com/postmarketOS/pmbootstrap/issues/429>
    "iter_time": "200",
    "jobs": str(multiprocessing.cpu_count() + 1),
    "kernel": "stable",
    "keymap": "",
    "log": "$WORK/log.txt",
    "mirror_alpine": "http://dl-cdn.alpinelinux.org/alpine/",
    "mirror_postmarketos": "http://postmarketos.brixit.nl",
    "nonfree_firmware": True,
    "nonfree_userland": False,
    "port_distccd": "33632",
    "qemu_native_mesa_driver": "dri-virtio",
    "ssh_keys": False,
    "timezone": "GMT",
    "ui": "weston",
    "user": "user",
    "work": os.path.expanduser("~") + "/.local/var/pmbootstrap",
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
    "$WORK/cache_ccache_$ARCH": "/mnt/pmbootstrap-ccache",
    "$WORK/cache_distfiles": "/var/cache/distfiles",
    "$WORK/cache_git": "/mnt/pmbootstrap-git",
    "$WORK/config_abuild": "/mnt/pmbootstrap-abuild-config",
    "$WORK/config_apk_keys": "/etc/apk/keys",
    "$WORK/packages": "/mnt/pmbootstrap-packages",
}

# Building chroots (all chroots, except for the rootfs_ chroot) get symlinks in
# the "pmos" user's home folder pointing to mountfolders from above.
chroot_home_symlinks = {
    "/mnt/pmbootstrap-abuild-config": "/home/pmos/.abuild",
    "/mnt/pmbootstrap-ccache": "/home/pmos/.ccache",
    "/mnt/pmbootstrap-git": "/home/pmos/git",
    "/mnt/pmbootstrap-packages": "/home/pmos/packages/pmos",
}

# Device nodes to be created in each chroot. Syntax for each entry:
# [permissions, type, major, minor, name]
chroot_device_nodes = [
    [666, "c", 1, 3, "null"],
    [666, "c", 1, 5, "zero"],
    [666, "c", 1, 7, "full"],
    [644, "c", 1, 8, "random"],
    [644, "c", 1, 9, "urandom"],
]

# Age in hours that we keep the APKINDEXes before downloading them again.
# You can force-update them with 'pmbootstrap update'.
apkindex_retention_time = 4

#
# BUILD
#
# Officially supported host/target architectures for postmarketOS. Only
# specify architectures supported by Alpine here. Fro cross-compiling,
# we need to generate the "musl-$ARCH", "binutils-$ARCH" and "gcc-$ARCH"
# packages (use "pmbootstrap aportgen musl-armhf" etc.).
build_device_architectures = ["armhf", "aarch64", "x86_64", "x86"]

# Packages, that will be installed in a chroot before it builds packages
# for the first time
build_packages = ["abuild", "build-base", "ccache"]

# fnmatch for supported pkgnames, that can be directly compiled inside
# the native chroot and a cross-compiler, without using distcc
build_cross_native = ["linux-*", "arch-bin-masquerade"]

# Necessary kernel config options
necessary_kconfig_options = {
    "all": {
        "ANDROID_PARANOID_NETWORK": False,
        "DEVTMPFS": True,
        "DEVTMPFS_MOUNT": False,
        "DM_CRYPT": True,
        "EXT4_FS": True,
        "PFT": False,
        "SYSVIPC": True,
        "VT": True
    },
    "armhf x86": {
        "LBDAF": True
    }
}

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
    "pkgdesc": {"array": False},
    "pkgrel": {"array": False},
    "pkgver": {"array": False},
    "provides": {"array": True},
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

    # Overridden packages
    "_pkgver": {"array": False},
}

# Variables from deviceinfo. Reference: <https://postmarketos.org/deviceinfo>
deviceinfo_attributes = [
    # general
    "format_version",
    "name",
    "manufacturer",
    "date",
    "dtb",
    "modules_initfs",
    "arch",
    "nonfree",

    # device
    "keyboard",
    "external_storage",
    "screen_width",
    "screen_height",
    "dev_touchscreen",
    "dev_touchscreen_calibration",
    "dev_keyboard",

    # bootloader
    "flash_method",

    # flash
    "flash_heimdall_partition_kernel",
    "flash_heimdall_partition_initfs",
    "flash_heimdall_partition_system",
    "generate_legacy_uboot_initfs",
    "kernel_cmdline",
    "generate_bootimg",
    "bootimg_qcdt",
    "flash_offset_base",
    "flash_offset_kernel",
    "flash_offset_ramdisk",
    "flash_offset_second",
    "flash_offset_tags",
    "flash_pagesize",
    "flash_fastboot_max_size",
    "flash_fastboot_vendor_id",
    "flash_sparse",

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

# Groups for the default user
install_user_groups = ["wheel", "video", "audio"]


#
# FLASH
#

flash_methods = ["fastboot", "heimdall", "0xffff", "none"]

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

Fastboot specific: $KERNEL_CMDLINE, $VENDOR_ID
Heimdall specific: $PARTITION_KERNEL, $PARTITION_INITFS
"""
flashers = {
    "fastboot": {
        "depends": ["android-tools"],
        "actions":
                {
                    "list_devices": [["fastboot", "-i", "$VENDOR_ID",
                                      "devices", "-l"]],
                    "flash_rootfs": [["fastboot", "-i", "$VENDOR_ID",
                                      "flash", "$PARTITION_SYSTEM", "$IMAGE"]],
                    "flash_kernel": [["fastboot", "-i", "$VENDOR_ID",
                                      "flash", "boot", "$BOOT/boot.img-$FLAVOR"]],
                    "boot": [["fastboot", "-i", "$VENDOR_ID",
                              "-c", "$KERNEL_CMDLINE", "boot",
                              "$BOOT/boot.img-$FLAVOR"]],
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
            "flash_rootfs": [
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
            "flash_rootfs": [
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


#
# APORTGEN
#
aportgen = {
    "cross": {
        "prefixes": ["binutils", "busybox-static", "gcc", "musl"],
        "confirm_overwrite": False,
    },
    "device": {
        "prefixes": ["device", "linux"],
        "confirm_overwrite": True,
    }
}

#
# QEMU
#
qemu_native_mesa_drivers = ["dri-swrast", "dri-virtio"]

#
# NEWAPKBUILD
# Options passed through to the "newapkbuild" command from Alpine Linux. They
# are duplicated here, so we can use Python's argparse for argument parsing and
# help page display. The -f (force) flag is not defined here, as we use that in
# the Python code only and don't pass it through.
#
newapkbuild_arguments_strings = [
    ["-n", "pkgname", "set package name (only use with SRCURL)"],
    ["-d", "pkgdesc", "set package description"],
    ["-l", "license", "set package license identifier from"
                      " <https://spdx.org/licenses/>"],
    ["-u", "url", "set package URL"],
]
newapkbuild_arguments_switches_pkgtypes = [
    ["-a", "autotools", "create autotools package (use ./configure ...)"],
    ["-C", "cmake", "create CMake package (assume cmake/ is there)"],
    ["-m", "meson", "create meson package (assume meson.build is there)"],
    ["-p", "perl", "create perl package (assume Makefile.PL is there)"],
    ["-y", "python", "create python package (assume setup.py is there)"],
]
newapkbuild_arguments_switches_other = [
    ["-s", "sourceforge", "use sourceforge source URL"],
    ["-c", "copy_samples", "copy a sample init.d, conf.d and install script"],
]
