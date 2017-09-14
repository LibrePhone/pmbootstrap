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
import argparse
import pmb.config
import pmb.parse.arch


def arguments_export(subparser):
    ret = subparser.add_parser("export", help="create convenience symlinks"
                               " to generated image files (system, kernel,"
                               " initramfs, boot.img, ...)")

    ret.add_argument("export_folder", help="export folder, defaults to"
                                           " /tmp/postmarketOS-export",
                     default="/tmp/postmarketOS-export", nargs="?")
    ret.add_argument("--odin", help="odin flashable tar"
                                    " (boot.img/kernel+initramfs only)",
                     action="store_true", dest="odin_flashable_tar")
    ret.add_argument("--flavor", default=None)
    return ret


def arguments_flasher(subparser):
    ret = subparser.add_parser("flasher", help="flash something to the"
                               " target device")
    sub = ret.add_subparsers(dest="action_flasher")
    ret.add_argument("--method", help="override flash method",
                     dest="flash_method", default=None)

    # Boot, flash kernel
    boot = sub.add_parser("boot", help="boot a kernel once")
    boot.add_argument("--cmdline", help="override kernel commandline")
    flash_kernel = sub.add_parser("flash_kernel", help="flash a kernel")
    for action in [boot, flash_kernel]:
        action.add_argument("--flavor", default=None)

    # Flash system
    flash_system = sub.add_parser("flash_system", help="flash the system partition")
    flash_system.add_argument("--partition", default=None, help="partition to flash"
                              " the system image")

    # Actions without extra arguments
    sub.add_parser("sideload", help="sideload recovery zip")
    sub.add_parser("list_flavors", help="list installed kernel flavors" +
                   " inside the device rootfs chroot on this computer")
    sub.add_parser("list_devices", help="show connected devices")

    # Deprecated "pmbootstrap flasher export"
    arguments_export(sub)
    return ret


def arguments_initfs(subparser):
    ret = subparser.add_parser(
        "initfs", help="do something with the initramfs")
    sub = ret.add_subparsers(dest="action_initfs")

    # hook ls
    sub.add_parser(
        "hook_ls",
        help="list available and installed hook packages")

    # hook add/del
    hook_add = sub.add_parser("hook_add", help="add a hook package")
    hook_del = sub.add_parser("hook_del", help="uninstall a hook package")
    for action in [hook_add, hook_del]:
        action.add_argument("hook", help="name of the hook aport, without the"
                            " '" + pmb.config.initfs_hook_prefix + "' prefix, for example: 'usb-shell'")

    # ls, build, extract
    ls = sub.add_parser("ls", help="list initramfs contents")
    build = sub.add_parser("build", help="(re)build the initramfs")
    extract = sub.add_parser(
        "extract",
        help="extract the initramfs to a temporary folder")
    for action in [ls, build, extract]:
        action.add_argument(
            "--flavor",
            default=None,
            help="name of the kernel flavor (run 'pmbootstrap flasher list_flavors'"
            " to get a list of all installed flavors")

    return ret


def arguments():
    parser = argparse.ArgumentParser(prog="pmbootstrap")

    # Other
    parser.add_argument("-V", "--version", action="version",
                        version=pmb.config.version)
    parser.add_argument("--no-cross", action="store_false", dest="cross",
                        help="disable crosscompiler, build only with qemu + gcc (slower!)")

    parser.add_argument("-a", "--alpine-version", dest="alpine_version",
                        help="examples: edge, latest-stable, v3.5")
    parser.add_argument("-c", "--config", dest="config",
                        default=pmb.config.defaults["config"])
    parser.add_argument("-d", "--port-distccd", dest="port_distccd")
    parser.add_argument("-mp", "--mirror-pmOS", dest="mirror_postmarketos")
    parser.add_argument("-m", "--mirror-alpine", dest="mirror_alpine")
    parser.add_argument("-j", "--jobs", help="parallel jobs when compiling")
    parser.add_argument("-p", "--aports",
                        help="postmarketos aports paths")
    parser.add_argument("-s", "--skip-initfs", dest="skip_initfs",
                        help="do not re-generate the initramfs",
                        action="store_true")
    parser.add_argument("-w", "--work", help="folder where all data"
                        " gets stored (chroots, caches, built packages)")
    parser.add_argument("-y", "--assume-yes", help="Assume 'yes' to all"
                        " question prompts. WARNING: this option will"
                        " cause normal 'are you sure?' prompts to be"
                        " disabled!",
                        action="store_true")

    # Logging
    parser.add_argument("-l", "--log", dest="log", default=None,
                        help="path to log file")
    parser.add_argument("--details-to-stdout", dest="details_to_stdout",
                        help="print details (e.g. build output) to stdout,"
                             " instead of writing to the log",
                        action="store_true")
    parser.add_argument("-v", "--verbose", dest="verbose",
                        action="store_true", help="write even more to the"
                        " logfiles (this may reduce performance)")
    parser.add_argument("-q", "--quiet", dest="quiet",
                        action="store_true", help="do not output any log messages")

    # Actions
    sub = parser.add_subparsers(title="action", dest="action")
    sub.add_parser("init", help="initialize config file")
    sub.add_parser("shutdown", help="umount, unregister binfmt")
    sub.add_parser("index", help="re-index all repositories with custom built"
                   " packages (do this after manually removing package files)")
    arguments_export(sub)
    arguments_flasher(sub)
    arguments_initfs(sub)

    # Action: log
    log = sub.add_parser("log", help="follow the pmbootstrap logfile")
    log_distccd = sub.add_parser(
        "log_distccd",
        help="follow the distccd logfile")
    for action in [log, log_distccd]:
        action.add_argument("-n", "--lines", default="60",
                            help="count of initial output lines")
        action.add_argument("-c", "--clear", help="clear the log",
                            action="store_true", dest="clear_log")

    # Action: zap
    zap = sub.add_parser("zap", help="safely delete chroot folders")
    zap.add_argument("-p", "--packages", action="store_true", help="also delete"
                     " the precious, self-compiled packages")
    zap.add_argument("-hc", "--http", action="store_true", help="also delete http"
                     "cache")
    zap.add_argument("-m", "--mismatch-bins", action="store_true", help="also delete"
                     " binary packages that are newer than the corresponding"
                     " package in aports")
    zap.add_argument("-d", "--distfiles", action="store_true", help="also delete"
                     " downloaded files cache")

    # Action: stats
    stats = sub.add_parser("stats", help="show ccache stats")
    stats.add_argument("--arch")

    # Action: build_init / chroot
    build_init = sub.add_parser("build_init", help="initialize build"
                                " environment (usually you do not need to call this)")
    chroot = sub.add_parser("chroot", help="start shell in chroot")
    chroot.add_argument("command", default=["sh"], help="command"
                        " to execute inside the chroot. default: sh", nargs='*')
    for action in [build_init, chroot]:
        suffix = action.add_mutually_exclusive_group()
        suffix.add_argument("-r", "--rootfs", action="store_true",
                            help="Chroot for the device root file system")
        suffix.add_argument("-b", "--buildroot", action="store_true",
                            help="Chroot for building packages for the device "
                                 "architecture")
        suffix.add_argument("-s", "--suffix", default=None,
                            help="Specify any chroot suffix, defaults to"
                                 " 'native'")

    # Action: install
    install = sub.add_parser("install", help="set up device specific" +
                             " chroot and install to sdcard or image file")
    install.add_argument("--sdcard", help="path to the sdcard device,"
                         " eg. /dev/mmcblk0")
    install.add_argument("--cipher", help="cryptsetup cipher used to"
                         " encrypt the system partition, eg. aes-xts-plain64")
    install.add_argument("--add", help="comma separated list of packages to be"
                         " added to the rootfs (e.g. 'vim,gcc')")
    install.add_argument("--no-fde", help="do not use full disk encryption",
                         action="store_false", dest="full_disk_encryption")
    install.add_argument("--flavor",
                         help="Specify kernel flavor to include in recovery"
                              " flashable zip", default=None)
    install.add_argument("--android-recovery-zip",
                         help="generate TWRP flashable zip",
                         action="store_true", dest="android_recovery_zip")
    install.add_argument("--recovery-flash-bootimg",
                         help="include kernel in recovery flashable zip",
                         action="store_true", dest="recovery_flash_bootimg")
    install.add_argument("--recovery-install-partition", default="system",
                         help="partition to flash from recovery,"
                              "eg. external_sd",
                         dest="recovery_install_partition")

    # Action: menuconfig / parse_apkbuild
    menuconfig = sub.add_parser("menuconfig", help="run menuconfig on"
                                " a kernel aport")
    parse_apkbuild = sub.add_parser("parse_apkbuild")
    for action in [menuconfig, parse_apkbuild]:
        action.add_argument("package")

    # Action: build / checksum / aportgen
    checksum = sub.add_parser("checksum", help="update aport checksums")
    aportgen = sub.add_parser("aportgen", help="generate a package build recipe"
                              " (aport/APKBUILD) based on an upstream aport from Alpine")
    build = sub.add_parser("build", help="create a package for a"
                           " specific architecture")
    build.add_argument("--arch")
    build.add_argument("--force", action="store_true")
    build.add_argument("--buildinfo", action="store_true")
    build.add_argument("--strict", action="store_true", help="(slower) zap and install only"
                       " required depends when building, to detect dependency errors")
    build.add_argument("--noarch-arch", dest="noarch_arch", default=None,
                       help="which architecture to use to build 'noarch'"
                            " packages. Defaults to the native arch normally,"
                            " and to the device arch when --strict is set."
                            " Override in case of strict mode failing on"
                            " dependencies, which only exist for a certain"
                            " arch.")
    for action in [checksum, build, aportgen]:
        action.add_argument("packages", nargs="+")

    # Action: challenge
    challenge = sub.add_parser("challenge",
                               help="verify, that all files in an apk can be"
                                    " reproduced from the same sources /"
                                    " verify, that an APKINDEX.tar.gz properly"
                                    " lists all apks in a repository folder")
    challenge.add_argument("--output-repo-changes", dest="output_repo_changes",
                           help="pass the path to a file here, to store a list"
                                " of apk- and APKINDEX-files that have been"
                                " changed during the build", default=None)
    challenge.add_argument("challenge_file",
                           help="the file to be verified. must end in"
                                " .apk, or must be named"
                                " APKINDEX.tar.gz.")

    # Action: parse_apkindex
    parse_apkindex = sub.add_parser("parse_apkindex")
    parse_apkindex.add_argument("apkindex_path")
    parse_apkindex.add_argument("package", default=None, nargs="?")

    # Action: config
    config = sub.add_parser("config",
                            help="get and set pmbootstrap options")
    config.add_argument("name", nargs="?", help="variable name")
    config.add_argument("value", nargs="?", help="set variable to value")

    # Action: qemu
    qemu = sub.add_parser("qemu")
    qemu.add_argument("--arch", choices=["aarch64", "arm", "x86_64"],
                      help="emulate a different architecture")
    qemu.add_argument("--cmdline", help="override kernel commandline")
    qemu.add_argument("-m", "--memory", type=int, default=1024,
                      help="guest RAM (default: 1024)")
    qemu.add_argument("-p", "--port", type=int, default=2222,
                      help="ssh port (default: 2222)")

    # Use defaults from the user's config file
    args = parser.parse_args()
    cfg = pmb.config.load(args)
    for varname in cfg["pmbootstrap"]:
        if varname not in args or not getattr(args, varname):
            value = cfg["pmbootstrap"][varname]
            if varname in pmb.config.defaults:
                default = pmb.config.defaults[varname]
                if isinstance(default, bool):
                    value = (value.lower() == "true")
            setattr(args, varname, value)

    # Replace $WORK in variables from user's config
    for varname in cfg["pmbootstrap"]:
        old = getattr(args, varname)
        if isinstance(old, str):
            setattr(args, varname, old.replace("$WORK", args.work))

    # Add convenience shortcuts
    setattr(args, "arch_native", pmb.parse.arch.alpine_native())

    # Add a caching dict (caches parsing of files etc. for the current session)
    setattr(args, "cache", {"apkindex": {},
                            "apkbuild": {},
                            "apk_min_version_checked": [],
                            "apk_repository_list_updated": [],
                            "aports_files_out_of_sync_with_git": None,
                            "find_aport": {}})

    # Add and verify the deviceinfo (only after initialization)
    if args.action != "init":
        setattr(args, "deviceinfo", pmb.parse.deviceinfo(args))
        arch = args.deviceinfo["arch"]
        if (arch != args.arch_native and
                arch not in pmb.config.build_device_architectures):
            raise ValueError("Arch '" + arch + "' is not officially enabled"
                             " in postmarketOS yet. However, this should be straight"
                             " forward. Simply enable it in pmb/config/__init__.py"
                             " in build_device_architectures, zap your package cache"
                             " (otherwise you will have issues with noarch packages)"
                             " and try again.")

    return args
