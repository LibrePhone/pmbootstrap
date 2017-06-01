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
import logging
import os
import multiprocessing

import pmb.config
import pmb.helpers.cli
import pmb.helpers.devices


def init(args):
    cfg = pmb.config.load(args)

    # Device
    devices = sorted(pmb.helpers.devices.list(args))
    logging.info("Target device (either an existing one, or a new one for"
                 " porting). Available: " + ", ".join(devices))
    cfg["pmbootstrap"]["device"] = pmb.helpers.cli.ask(args, "Device",
                                                       None, args.device)

    # Work folder
    logging.info("Location of the 'work' path. Multiple chroots (native,"
                 " device arch, device rootfs) will be created in there.")
    cfg["pmbootstrap"]["work"] = pmb.helpers.cli.ask(args, "Work path",
                                                     None, args.work, False)
    os.makedirs(cfg["pmbootstrap"]["work"], 0o700, True)

    # Parallel job count
    default = args.jobs
    if not default:
        default = multiprocessing.cpu_count() + 1
    logging.info("How many jobs should run parallel on this machine, when"
                 " compiling?")
    cfg["pmbootstrap"]["jobs"] = pmb.helpers.cli.ask(args, "Jobs",
                                                     None, default)

    # Save config
    pmb.config.save(args, cfg)

    logging.info(
        "WARNING: The applications in the chroots do not get updated automatically.")
    logging.info("Run 'pmbootstrap zap' to delete all chroots once a day before"
                 " working with pmbootstrap!")
    logging.info("It only takes a few seconds, and all packages are cached.")

    logging.info("Done!")
