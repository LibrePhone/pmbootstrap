#!/usr/bin/env python3

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

import sys
import logging
import os
import json
import traceback

import pmb.aportgen
import pmb.build
import pmb.config
import pmb.challenge
import pmb.chroot
import pmb.chroot.initfs
import pmb.chroot.other
import pmb.flasher
import pmb.helpers.logging
import pmb.helpers.other
import pmb.helpers.run
import pmb.parse
import pmb.install


def action_aportgen(args):
    pmb.aportgen.generate(args, args.package)


def action_build(args):
    pmb.build.package(args, args.package, args.arch, args.force,
                      args.buildinfo)


def action_build_init(args):
    pmb.build.init(args, args.suffix)


def action_challenge(args):
    pmb.challenge.frontend(args)


def action_checksum(args):
    pmb.build.checksum(args, args.package)


def action_chroot(args):
    pmb.chroot.apk.check_min_version(args, args.suffix)
    pmb.chroot.root(args, args.command, args.suffix, log=False)


def action_index(args):
    pmb.build.index_repo(args)


def action_initfs(args):
    pmb.chroot.initfs.frontend(args)


def action_install(args):
    pmb.install.install(args)


def action_flasher(args):
    pmb.flasher.frontend(args)


def action_menuconfig(args):
    pmb.build.menuconfig(args, args.package, args.deviceinfo["arch"])


def action_parse_apkbuild(args):
    build_path = args.aports + "/" + args.package + "/APKBUILD"
    print(json.dumps(pmb.parse.apkbuild(args, build_path), indent=4))


def action_parse_apkindex(args):
    result = pmb.parse.apkindex.parse(args, args.apkindex_path)
    print(json.dumps(result, indent=4))


def action_shutdown(args):
    pmb.chroot.shutdown(args)


def action_stats(args):
    pmb.build.ccache_stats(args, args.arch)


def action_log(args):
    pmb.helpers.run.user(args, ["tail", "-f", args.log, "-n", args.lines],
                         log=False)


def action_log_distccd(args):
    logpath = "/home/user/distccd.log"
    pmb.chroot.user(args, ["tail", "-f", logpath, "-n", args.lines], log=False)


def action_zap(args):
    pmb.chroot.zap(args)


def main():
    # Parse arguments, set up logging
    args = pmb.parse.arguments()
    pmb.helpers.logging.init(args)

    # Wrap everything to display nice error messages
    try:
        # Sanity check
        pmb.helpers.other.check_grsec(args)

        # Initialize or require config
        if args.action == "init":
            return pmb.config.init(args)
        elif not os.path.exists(args.config):
            logging.critical("Please specify a config file, or run"
                             " 'pmbootstrap init' to generate one.")
            return 1

        # If an action_xxx function is defined in local scope, run it with args
        func = locals().get('action_' + args.action)
        if func:
            func(args)
        else:
            logging.info("Run pmbootstrap -h for usage information.")

        # Print finish timestamp
        logging.info("Done")

    except Exception as e:
        logging.info("ERROR: " + str(e))
        logging.info("Run 'pmbootstrap log' for details.")
        logging.info("See also: <https://postmarketos.org/troubleshooting>")
        logging.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
