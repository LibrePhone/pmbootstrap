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
import pmb.chroot
import pmb.chroot.other
import pmb.flasher
import pmb.helpers.logging
import pmb.helpers.run
import pmb.parse
import pmb.install


def main():
    try:
        # Parse arguments
        args = pmb.parse.arguments()
        pmb.helpers.logging.init(args)

        # Initialize or require config
        if args.action == "init":
            return pmb.config.init(args)
        if not os.path.exists(args.config):
            logging.critical("Please specify a config file, or run"
                             " 'pmbootstrap init' to generate one.")
            return 1

        # All other actions
        if args.action == "aportgen":
            pmb.aportgen.generate(args, args.package)
        elif args.action == "build":
            pmb.build.package(args, args.package, args.arch, args.force, False)
        elif args.action == "build_init":
            pmb.build.init(args, args.suffix)
        elif args.action == "checksum":
            pmb.build.checksum(args, args.package)
        elif args.action == "chroot":
            pmb.chroot.root(args, args.command, args.suffix, log=False)
        elif args.action == "index":
            pmb.build.index_repo(args)
        elif args.action == "install":
            pmb.install.install(args)
        elif args.action == "flasher":
            pmb.flasher.frontend(args)
        elif args.action == "menuconfig":
            pmb.build.menuconfig(args, args.package, args.deviceinfo["arch"])
        elif args.action == "parse_apkbuild":
            print(json.dumps(pmb.parse.apkbuild(args.aports + "/" +
                                                args.package + "/APKBUILD"), indent=4))
        elif args.action == "shutdown":
            pmb.chroot.shutdown(args)
        elif args.action == "stats":
            pmb.build.ccache_stats(args, args.arch)
        elif args.action == "log":
            pmb.helpers.run.user(args, ["tail", "-f", args.log,
                                 "-n", args.lines], log=False)
        elif args.action == "log_distccd":
            pmb.chroot.user(args, ["tail", "-f", "/home/user/distccd.log",
                            "-n", args.lines], log=False)
        elif args.action == "zap":
            pmb.chroot.zap(args)
        else:
            logging.info("Run pmbootstrap -h for usage information.")

        # Print finish timestamp
        logging.info("Done")

    except Exception as e:
        logging.info("ERROR: " + str(e))
        logging.info("Run 'pmbootstrap log' for details.")
        logging.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
