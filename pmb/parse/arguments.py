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


def arguments_flasher(subparser):
    ret = subparser.add_parser("flasher", help="flash something to the"
                               " target device")
    sub = ret.add_subparsers(dest="action_flasher")

    # Other
    sub.add_parser("flash_system", help="flash the system partition")
    sub.add_parser("list_flavors", help="list installed kernel flavors" +
                   " inside the device rootfs chroot on this computer")
    sub.add_parser("list_devices", help="show connected devices")

    # Boot, flash kernel
    boot = sub.add_parser("boot", help="boot a kernel once")
    flash_kernel = sub.add_parser("flash_kernel", help="flash a kernel")
    for action in [boot, flash_kernel]:
        action.add_argument("--flavor", default=None)

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
    parser.add_argument("-m", "--mirror-alpine", dest="mirror_alpine")
    parser.add_argument("-j", "--jobs", help="parallel jobs when compiling")
    parser.add_argument("-p", "--aports",
                        help="postmarketos aports paths")
    parser.add_argument("-w", "--work", help="folder where all data"
                        " gets stored (chroots, caches, built packages)")

    # Logging
    parser.add_argument("-l", "--log", dest="log", default=None)
    parser.add_argument("-v", "--verbose", dest="verbose",
                        action="store_true", help="output the source file, where the log"
                        " message originated from with each log message")
    parser.add_argument("-q", "--quiet", dest="quiet",
                        action="store_true", help="do not output any log messages")

    # Actions
    sub = parser.add_subparsers(title="action", dest="action")
    sub.add_parser("init", help="initialize config file")
    sub.add_parser("shutdown", help="umount, unregister binfmt")
    sub.add_parser("index", help="re-index all repositories with custom built"
                   " packages (do this after manually removing package files)")
    arguments_flasher(sub)

    # Action: log
    log = sub.add_parser("log", help="follow the pmbootstrap logfile")
    log_distccd = sub.add_parser("log_distccd", help="follow the distccd logfile")
    for action in [log, log_distccd]:
        action.add_argument("-n", "--lines", default="30", help="count of initial output lines")

    # Action: zap
    zap = sub.add_parser("zap", help="safely delete chroot"
                         "folders")
    zap.add_argument("-p", "--packages", action="store_true", help="also delete"
                     " the precious, self-compiled packages")
    zap.add_argument("-hc", "--http", action="store_true", help="also delete http"
                     "cache")

    # Action: stats
    stats = sub.add_parser("stats", help="show ccache stats")
    stats.add_argument("--arch")

    # Action: chroot / build_init / kernel
    build_init = sub.add_parser("build_init", help="initialize build"
                                " environment (usually you do not need to call this)")
    chroot = sub.add_parser("chroot", help="start shell in chroot")
    chroot.add_argument("command", default=["sh"], help="command"
                        " to execute inside the chroot. default: sh", nargs='*')
    for action in [build_init, chroot]:
        action.add_argument("--suffix", default="native")

    # Action: install
    install = sub.add_parser("install", help="set up device specific" +
                             " chroot and install to sdcard or image file")
    install.add_argument("--sdcard", help="path to the sdcard device,"
                         " eg. /dev/mmcblk0")
    install.add_argument("--cipher", help="cryptsetup cipher used to"
                         " encrypt the system partition, eg. aes-xts-plain64")
    install.add_argument("--add", help="comma separated list of packages to be"
                         " added to the rootfs (e.g. 'vim,gcc')")

    # Action: build / checksum / menuconfig / parse_apkbuild / aportgen
    menuconfig = sub.add_parser("menuconfig", help="run menuconfig on"
                                " a kernel aport")
    checksum = sub.add_parser("checksum", help="update aport checksums")
    parse_apkbuild = sub.add_parser("parse_apkbuild")
    aportgen = sub.add_parser("aportgen", help="generate a package build recipe"
                              " (aport/APKBUILD) based on an upstream aport from Alpine")
    build = sub.add_parser("build", help="create a package for a"
                           " specific architecture")
    build.add_argument("--arch")
    build.add_argument("--force", action="store_true")
    for action in [checksum, build, menuconfig, parse_apkbuild, aportgen]:
        action.add_argument("package")

    # Use defaults from the user's config file
    args = parser.parse_args()
    cfg = pmb.config.load(args)
    for varname in cfg["pmbootstrap"]:
        if varname not in args or not getattr(args, varname):
            setattr(args, varname, cfg["pmbootstrap"][varname])

    # Replace $WORK in variables from user's config
    for varname in cfg["pmbootstrap"]:
        old = getattr(args, varname)
        setattr(args, varname, old.replace("$WORK", args.work))

    # Add convinience shortcuts
    setattr(args, "arch_native", pmb.parse.arch.alpine_native())

    # Add the deviceinfo (only after initialization)
    if args.action != "init":
        setattr(args, "deviceinfo", pmb.parse.deviceinfo(args))

    return args
