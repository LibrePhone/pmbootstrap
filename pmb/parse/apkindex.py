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
import distutils.version
import glob
import os
import tarfile


def compare_version(a_str, b_str):
    """
    http://stackoverflow.com/a/11887885
    LooseVersion behaves just like apk's version check, at least
    for all package versions, that have "-r".

    :returns:
        (a <  b): -1
        (a == b):  0
        (a >  b):  1
    """
    if a_str is None:
        a_str = "0"
    if b_str is None:
        b_str = "0"
    a = distutils.version.LooseVersion(a_str)
    b = distutils.version.LooseVersion(b_str)
    if a < b:
        return -1
    if a == b:
        return 0
    return 1


def read(args, package, path, must_exist=True):
    """
    :param path: Path to APKINDEX.tar.gz, defaults to $WORK/APKINDEX.tar.gz
    :param package: The package of which you want to read the properties.
    :param must_exist: When set to true, raise an exception when the package is
        missing in the index, or the index file was not found.
    :returns: {"pkgname": ..., "version": ..., "depends": [...]}
        When the package appears multiple times in the APKINDEX, this
        function returns the attributes of the latest version.
    """
    # Verify APKINDEX path
    if not os.path.exists(path):
        if not must_exist:
            return None
        raise RuntimeError("File not found: " + path)

    # Read the tarfile
    ret = None
    with tarfile.open(path, "r:gz") as tar:
        with tar.extractfile(tar.getmember("APKINDEX")) as handle:
            current = {}
            for line in handle:
                line = line.decode()
                if line == "\n":  # end of package
                    if current["pkgname"] == package:
                        if not ret or compare_version(current["version"],
                                                      ret["version"]) == 1:
                            ret = current
                    if "provides" in current:
                        for alias in current["provides"]:
                            split = alias.split("=")
                            if len(split) == 1:
                                continue
                            name = split[0]
                            version = split[1]
                            if name == package:
                                if not ret or compare_version(current["version"],
                                                              version) == 1:
                                    ret = current
                    current = {}
                if line.startswith("P:"):  # package
                    current["pkgname"] = line[2:-1]
                if line.startswith("V:"):  # version
                    current["version"] = line[2:-1]
                if line.startswith("D:"):  # depends
                    depends = line[2:-1]
                    if depends:
                        current["depends"] = depends.split(" ")
                    else:
                        current["depends"] = []
                if line.startswith("p:"):  # provides
                    provides = line[2:-1]
                    current["provides"] = provides.split(" ")
    if not ret and must_exist:
        raise RuntimeError("Package " + package + " not found in " + path)

    if ret:
        for key in ["depends", "provides"]:
            if key not in ret:
                ret[key] = []

    return ret


def read_any_index(args, package, arch=None):
    """
    Check if *any* APKINDEX has a specific package.

    :param arch: defaults to native architecture
    """
    if not arch:
        arch = args.arch_native
    indexes = [args.work + "/packages/" + arch + "/APKINDEX.tar.gz"]
    pattern = args.work + "/cache_apk_" + arch + "/APKINDEX.*.tar.gz"
    indexes += glob.glob(pattern)

    for index in indexes:
        index_data = read(args, package, index, False)
        if index_data:
            return index_data
    return None
