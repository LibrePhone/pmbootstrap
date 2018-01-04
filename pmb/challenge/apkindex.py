"""
Copyright 2018 Oliver Smith

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
import glob
import logging
import pmb.parse.apkindex


def apkindex(args, path_apkindex, apk_suffix=""):
    """
    Verify an APKINDEX.tar.gz file, and its repository folder:
    - Each apk must be defined inside the APKINDEX (once!)
    - There must be no extra files

    :param path_apkindex: full path to the APKINDEX.tar.gz
    :param apk_suffix: set this to ".unverified", if all apk files in
                       the repository have such a suffix appended.
    """
    # Parse the apkindex file
    content = pmb.parse.apkindex.parse(args, path_apkindex, True)
    folder = os.path.dirname(path_apkindex)

    # All listed packages must exist
    found = []
    count = str(len(content.items()))
    logging.info("Check for existence of all listed packages (" + count + ")")
    for pkgname_alias, block in content.items():
        apk = (block["pkgname"] + "-" + block["version"] + ".apk" +
               apk_suffix)
        if not os.path.exists(folder + "/" + apk):
            raise RuntimeError("Could not find file '" + apk +
                               "' mentioned in " + path_apkindex)
        # Mark the apk and its buildinfo (if it exists) as found
        if apk not in found:
            found.append(apk)
            buildinfo = (block["pkgname"] + "-" + block["version"] +
                         ".apk.buildinfo.json")
            if os.path.exists(folder + "/" + buildinfo):
                found.append(buildinfo)
            # Add diff files, if they exist
            for name in [apk + ".diff.md", buildinfo + ".diff.md"]:
                if os.path.exists(folder + "/" + name):
                    found.append(name)

    # There must be no extra files
    logging.info("Check for extra files")
    for path in glob.glob(folder + "/*"):
        name = os.path.basename(path)
        if name == "APKINDEX.tar.gz" or name in found:
            continue
        raise RuntimeError("Unexpected file '" + name + "' inside the"
                           " repository folder: " + folder)
