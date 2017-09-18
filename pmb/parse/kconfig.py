"""
Copyright 2017 Attila Szollosi

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
import glob
import logging
import re
import os

import pmb.build
import pmb.config


def is_set(config, option):
    """
    Check, whether a boolean or tristate option is enabled
    either as builtin or module.
    """
    return re.search("^CONFIG_" + option + "=[ym]", config, re.M) is not None


def check(args, pkgname, details=False):
    """
    Check for necessary kernel config options.

    :returns: True when the check was successful, False otherwise
    """
    # Pkgname: allow omitting "linux-" prefix
    if pkgname.startswith("linux-"):
        flavor = pkgname.split("linux-")[1]
        logging.info("PROTIP: You can simply do 'pmbootstrap kconfig_check " +
                     flavor + "'")
    else:
        flavor = pkgname

    # Read all kernel configs in the aport
    ret = True
    aport = pmb.build.find_aport(args, "linux-" + flavor)
    for config_path in glob.glob(aport + "/config-*"):
        logging.debug("Check kconfig: " + config_path)
        with open(config_path) as handle:
            config = handle.read()

        # Loop trough necessary config options, and print a warning,
        # if any is missing
        path = "linux-" + flavor + "/" + os.path.basename(config_path)
        for key, value in pmb.config.necessary_kconfig_options.items():
            if value not in [True, False]:
                raise RuntimeError("kconfig check code can only handle"
                                   " True/False right now, given value '" +
                                   str(value) + "' is not supported. If you"
                                   " need this, please open an issue.")
            if value != is_set(config, key):
                ret = False
                if details:
                    should = "should" if value else "should *not*"
                    link = ("https://wiki.postmarketos.org/wiki/"
                            "Kernel_configuration#CONFIG_" + key)
                    logging.info("WARNING: " + path + ": CONFIG_" + key + " " +
                                 should + " be set. See <" + link +
                                 "> for details.")
                else:
                    logging.warning("WARNING: " + path + " isn't configured"
                                    " properly for postmarketOS, run"
                                    " 'pmbootstrap kconfig_check' for"
                                    " details!")
                    break
    return ret
