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
import json
import os
import pmb.build
import pmb.parse.apkbuild
import pmb.helpers.repo
import pmb.challenge


def build(args, apk_path):
    # Parse buildinfo
    buildinfo_path = apk_path + ".buildinfo.json"
    if not os.path.exists(buildinfo_path):
        logging.info("NOTE: To create a .buildinfo.json file, use the"
                     " --buildinfo command while building: 'pmbootstrap build"
                     " --buildinfo <pkgname>'")
        raise RuntimeError("Missing file: " + buildinfo_path)
    with open(buildinfo_path) as handle:
        buildinfo = json.load(handle)

    # Install all listed packages
    pmb.chroot.apk.install(args, buildinfo["versions"].keys())

    # Verify the installed versions
    installed = pmb.chroot.apk.installed(args)
    for pkgname, version in buildinfo["versions"].items():
        version_installed = installed[pkgname]["version"]
        if version_installed != version:
            raise RuntimeError("Dependency " + pkgname + " version is different"
                               " (installed: " + version_installed + ","
                               " buildinfo: " + version + ")!")
    # Build the package
    repo_before = pmb.helpers.repo.files(args)
    pmb.build.package(args, buildinfo["pkgname"], buildinfo["arch"],
                      force=True, buildinfo=True)
    repo_diff = pmb.helpers.repo.diff(args, repo_before)

    # Diff the apk contents
    staging_path = os.path.realpath(os.path.dirname(apk_path) + "/../")
    for file in repo_diff:
        file_staging = staging_path + "/" + file
        file_work = args.work + "/packages/" + file

        if file.endswith(".apk"):
            logging.info("Verify " + file)
            pmb.challenge.apk(args, file_staging, file_work)
        elif (file.endswith("/APKINDEX.tar.gz") or
              file.endswith(".apk.buildinfo.json")):
            # We only verify the apk file (see above). The APKINDEX can
            # be verified separately.
            continue
        else:
            raise RuntimeError("Unknown file type changed in the"
                               " package repository folder: " + file)

    # Output the changed files from the repository
    if args.output_repo_changes:
        with open(args.output_repo_changes, "w") as handler:
            for file in repo_diff:
                handler.write(file + "\n")
