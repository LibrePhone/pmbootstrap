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
import os
import logging
import pmb.aportgen.binutils
import pmb.aportgen.busybox_static
import pmb.aportgen.device
import pmb.aportgen.gcc
import pmb.aportgen.linux
import pmb.aportgen.musl
import pmb.config
import pmb.helpers.cli


def properties(pkgname):
    """
    Get the `pmb.config.aportgen` properties for the aport generator, based on
    the pkgname prefix.

    Example: "musl-armhf" => ("musl", "cross", {"confirm_overwrite": False})

    :param pkgname: package name
    :returns: (prefix, folder, options)
    """
    for folder, options in pmb.config.aportgen.items():
        for prefix in options["prefixes"]:
            if pkgname.startswith(prefix):
                return (prefix, folder, options)
    raise ValueError("No generator available for " + pkgname + "!")


def generate(args, pkgname):
    # Confirm overwrite
    prefix, folder, options = properties(pkgname)
    path_target = args.aports + "/" + folder + "/" + pkgname
    if options["confirm_overwrite"] and os.path.exists(path_target):
        logging.warning("WARNING: Target folder already exists: " + path_target)
        if not pmb.helpers.cli.confirm(args, "Continue and overwrite?"):
            raise RuntimeError("Aborted.")

    # Run pmb.aportgen.PREFIX.generate()
    if os.path.exists(args.work + "/aportgen"):
        pmb.helpers.run.user(args, ["rm", "-r", args.work + "/aportgen"])
    getattr(pmb.aportgen, prefix.replace("-", "_")).generate(args, pkgname)

    # Move to the aports folder
    if os.path.exists(path_target):
        pmb.helpers.run.user(args, ["rm", "-r", path_target])
    pmb.helpers.run.user(
        args, ["mv", args.work + "/aportgen", path_target])
