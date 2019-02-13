# PYTHON_ARGCOMPLETE_OK
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
    # Wrap everything to display nice error messages
    args = None
    try:
        # Parse arguments, set up logging
        args = parse.arguments()
        os.umask(0o22)

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
        # Dump log to stdout when args (and therefore logging) init failed
        if not args:
            logging.getLogger().setLevel(logging.DEBUG)

        logging.info("ERROR: " + str(e))
        logging.info("See also: <https://postmarketos.org/troubleshooting>")
        logging.debug(traceback.format_exc())

        # Hints about the log file (print to stdout only)
        log_hint = "Run 'pmbootstrap log' for details."
        if not args or not os.path.exists(args.log):
            log_hint += (" Alternatively you can use '--details-to-stdout' to"
                         " get more output, e.g. 'pmbootstrap --details-to-stdout"
                         " init'.")
        print(log_hint)
        return 1


if __name__ == "__main__":
    sys.exit(main())
