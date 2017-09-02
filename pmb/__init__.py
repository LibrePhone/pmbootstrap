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
import traceback

from . import config
from . import parse
from .helpers import frontend
from .helpers import logging as pmb_logging
from .helpers import other


def main():
    # Parse arguments, set up logging
    args = parse.arguments()
    pmb_logging.init(args)

    # Wrap everything to display nice error messages
    try:
        # Sanity check
        other.check_grsec(args)

        # Initialize or require config
        if args.action == "init":
            return config.init(args)
        elif not os.path.exists(args.config):
            logging.critical("Please specify a config file, or run"
                             " 'pmbootstrap init' to generate one.")
            return 1

        # Run the function with the action's name (in pmb/helpers/frontend.py)
        if args.action:
            getattr(frontend, args.action)(args)
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
