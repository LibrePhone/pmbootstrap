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
import pmb.config


def deviceinfo(args, device=None):
    """
    :param device: defaults to args.device
    """
    if not device:
        device = args.device

    aport = args.aports + "/device/device-" + device
    if not os.path.exists(aport) or not os.path.exists(aport + "/deviceinfo"):
        logging.fatal("You will need to create a device-specific package")
        logging.fatal("before you can continue. Please create at least the")
        logging.fatal("following files:")
        logging.fatal(aport + "/APKBUILD")
        logging.fatal(aport + "/deviceinfo")
        raise RuntimeError("Incomplete device information")

    ret = {}
    path = aport + "/deviceinfo"
    with open(path) as handle:
        for line in handle:
            if not line.startswith("deviceinfo_"):
                continue
            if "=" not in line:
                raise SyntaxError(path + ": No '=' found:\n\t" + line)
            split = line.split("=", 1)
            key = split[0][len("deviceinfo_"):]
            value = split[1].replace("\"", "").replace("\n", "")
            ret[key] = value

    # Assign empty string as default
    for key in pmb.config.deviceinfo_attributes:
        if key not in ret:
            ret[key] = ""

    return ret
