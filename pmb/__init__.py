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
import sys
import logging
import os
import traceback

from . import config
from . import parse
from .config import init as config_init
from .helpers import frontend
from .helpers import logging as pmb_logging
from .helpers import mount
from .helpers import other


def main():
    # Parse arguments, set up logging
    args = parse.arguments()
    pmb_logging.init(args)
    os.umask(0o22)

    # Wrap everything to display nice error messages
    try:
        # Sanity checks
        other.check_grsec(args)
        if not args.as_root and os.geteuid() == 0:
            raise RuntimeError("Do not run pmbootstrap as root!")

        # Initialize or require config
        if args.action == "init":
            return config_init.frontend(args)
        elif not os.path.exists(args.config):
            raise RuntimeError("Please specify a config file, or run"
                               " 'pmbootstrap init' to generate one.")
        elif not os.path.exists(args.work):
            raise RuntimeError("Work path not found, please run 'pmbootstrap"
                               " init' to create it.")

        # Migrate work folder if necessary
        if args.action not in ["shutdown", "zap", "log"]:
            other.migrate_work_folder(args)

        # Run the function with the action's name (in pmb/helpers/frontend.py)
        if args.action:
            getattr(frontend, args.action)(args)
        else:
            logging.info("Run pmbootstrap -h for usage information.")

        # Still active notice
        if mount.ismount(args.work + "/chroot_native/dev"):
            logging.info("NOTE: chroot is still active (use 'pmbootstrap"
                         " shutdown' as necessary)")
        logging.info("Done")

    except Exception as e:
        logging.info("ERROR: " + str(e))
        logging.info("See also: <https://postmarketos.org/troubleshooting>")
        logging.debug(traceback.format_exc())

        # Hints about the log file (print to stdout only)
        if os.path.exists(args.log):
            print("Run 'pmbootstrap log' for details.")
        else:
            print("Crashed before the log file was created.")
            print("Running init again like the following gives more details:")
            print("    pmbootstrap --details-to-stdout init")
        return 1


if __name__ == "__main__":
    sys.exit(main())
