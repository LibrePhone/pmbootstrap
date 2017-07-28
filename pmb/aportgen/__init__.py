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
import pmb.aportgen.musl
import pmb.aportgen.gcc
import pmb.aportgen.busybox_static
import pmb.helpers.git


def generate(args, pkgname):
    # Prepare git repo and temp folder
    pmb.helpers.git.clone(args, "aports_upstream")
    logging.info("(native) generate " + pkgname + " aport")
    if os.path.exists(args.work + "/aportgen"):
        pmb.helpers.run.user(args, ["rm", "-r", args.work + "/aportgen"])

    # Choose generator based on the name
    if pkgname.startswith("binutils-"):
        pmb.aportgen.binutils.generate(args, pkgname)
    elif pkgname.startswith("musl-"):
        pmb.aportgen.musl.generate(args, pkgname)
    elif pkgname.startswith("gcc-"):
        pmb.aportgen.gcc.generate(args, pkgname)
    elif pkgname.startswith("busybox-static-"):
        pmb.aportgen.busybox_static.generate(args, pkgname)
    else:
        raise ValueError("No generator available for " + pkgname + "!")

    # Move to the aports folder
    path_target = args.aports + "/cross/" + pkgname
    if os.path.exists(path_target):
        pmb.helpers.run.user(args, ["rm", "-r", path_target])
    pmb.helpers.run.user(
        args, ["mv", args.work + "/aportgen", path_target])
