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
import logging
import pmb.config

# Get magic and mask from binfmt info file
# Return: {magic: ..., mask: ...}


def binfmt_info(args, arch_qemu):
    # Parse the info file
    full = {}
    info = pmb.config.pmb_src + "/pmb/data/qemu-user-binfmt.txt"
    logging.verbose("parsing: " + info)
    with open(info, "r") as handle:
        for line in handle:
            if line.startswith('#') or "=" not in line:
                continue
            splitted = line.split("=")
            key = splitted[0].strip()
            value = splitted[1]
            full[key] = value[1:-2]

    ret = {}
    logging.verbose("filtering by architecture: " + arch_qemu)
    for type in ["mask", "magic"]:
        key = arch_qemu + "_" + type
        if key not in full:
            raise RuntimeError("Could not find key " + key + " in binfmt info file: " +
                               info)
        ret[type] = full[key]
    logging.verbose("=> " + str(ret))
    return ret
