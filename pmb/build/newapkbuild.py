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
import glob
import os
import logging
import pmb.chroot.user
import pmb.helpers.cli
import pmb.parse


def newapkbuild(args, folder, args_passed, force=False):
    # Initialize build environment and build folder
    pmb.build.init(args)
    build = "/home/pmos/build"
    build_outside = args.work + "/chroot_native" + build
    if os.path.exists(build_outside):
        pmb.chroot.root(args, ["rm", "-r", build])
    pmb.chroot.user(args, ["mkdir", "-p", build])

    # Run newapkbuild
    pmb.chroot.user(args, ["newapkbuild"] + args_passed, working_dir=build)
    glob_result = glob.glob(build_outside + "/*/APKBUILD")
    if not len(glob_result):
        return

    # Paths for copying
    source_apkbuild = glob_result[0]
    pkgname = pmb.parse.apkbuild(args, source_apkbuild, False)["pkgname"]
    target = args.aports + "/" + folder + "/" + pkgname

    # Move /home/pmos/build/$pkgname/* to /home/pmos/build/*
    for path in glob.glob(build_outside + "/*/*"):
        path_inside = build + "/" + pkgname + "/" + os.path.basename(path)
        pmb.chroot.user(args, ["mv", path_inside, build])
    pmb.chroot.user(args, ["rmdir", build + "/" + pkgname])

    # Overwrite confirmation
    if os.path.exists(target):
        logging.warning("WARNING: Folder already exists: " + target)
        question = "Continue and delete its contents?"
        if not force and not pmb.helpers.cli.confirm(args, question):
            raise RuntimeError("Aborted.")
        pmb.helpers.run.user(args, ["rm", "-r", target])

    # Copy the aport (without the extracted src folder)
    logging.info("Create " + target)
    pmb.helpers.run.user(args, ["mkdir", "-p", target])
    for path in glob.glob(build_outside + "/*"):
        if not os.path.isdir(path):
            pmb.helpers.run.user(args, ["cp", path, target])
