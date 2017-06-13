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
import glob
import os


def files(args):
    """
    Returns all files (apk/buildinfo) with their last modification timestamp
    inside the package repository, sorted by architecture.

    :returns: {"x86_64": {"first.apk": last_modified_timestamp, ... }, ... }
    """
    ret = {}
    for arch_folder in glob.glob(args.work + "/packages/*"):
        arch = os.path.basename(arch_folder)
        ret[arch] = {}
        for file in glob.glob(arch_folder + "/*"):
            basename = os.path.basename(file)
            ret[arch][basename] = os.path.getmtime(file)
    return ret


def diff(args, files_a, files_b=None):
    """
    Returns a list of files, that have been added or modified inside the
    package repository.

    :param files_a: return value from pmb.helpers.repo.files()
    :param files_b: defaults to creating a new list
    :returns: ["x86_64/APKINDEX.tar.gz", "x86_64/package.apk",
               "x86_64/package.buildinfo", ...]
    """
    if not files_b:
        files_b = files(args)

    ret = []
    for arch in files_b.keys():
        for file, timestamp in files_b[arch].items():
            if (arch not in files_a or file not in files_a[arch] or
                    timestamp is not files_a[arch][file]):
                ret.append(arch + "/" + file)

    return sorted(ret)
