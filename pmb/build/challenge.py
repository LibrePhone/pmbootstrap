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
import tarfile
import tempfile
import filecmp
import shutil
import pmb.build
import pmb.parse.apkbuild
import pmb.parse.other
import pmb.helpers.repo


def diff_files(tar_a, tar_b, member_a, member_b, name):
    # Extract both files
    tars = [tar_a, tar_b]
    members = [member_a, member_b]
    temp_files = []
    for i in range(2):
        handle, path = tempfile.mkstemp("pmbootstrap")
        handle = open(handle, "wb")
        shutil.copyfileobj(tars[i].extractfile(members[i]), handle)
        handle.close()
        temp_files.append(path)

    # Compare and delete
    equal = filecmp.cmp(temp_files[0], temp_files[1], shallow=False)
    for temp_file in temp_files:
        os.remove(temp_file)
    if equal:
        logging.debug("=> OK!")
    else:
        raise RuntimeError("File '" + name + "' is different!")


def tar_getnames_without_signature(tar, tar_name):
    """
    The signature file name is always different.
    This function raises an exception, when the number of signature
    files in the archive is not 1.
    :returns: a sorted list of all filenames inside the tar archive,
              except for the signature file.
    """
    names = tar.getnames()
    found = False
    ret = []
    for name in names:
        if name.startswith(".SIGN.RSA."):
            if found:
                raise RuntimeError("More than one signature file found"
                                   " inside " + tar_name + ": " +
                                   str(names))
            else:
                found = True
        else:
            ret.append(name)

    if not found:
        raise RuntimeError("No signature file found inside " +
                           tar_name + ": " + str(names))
    return sorted(ret)


def diff(args, apk_a, apk_b):
    with tarfile.open(apk_a, "r:gz") as tar_a:
        with tarfile.open(apk_b, "r:gz") as tar_b:
            # List of files must be the same
            list_a = tar_getnames_without_signature(tar_a, apk_a)
            list_b = tar_getnames_without_signature(tar_b, apk_b)
            if list_a != list_b:
                logging.info("Files in " + apk_a + ":" + str(list_a))
                logging.info("Files in " + apk_b + ":" + str(list_b))
                raise RuntimeError(
                    "Both APKs do not contain the same file names!")

            # Iterate through the list
            success = True
            for name in list_a:
                try:
                    logging.debug("Compare: " + name)
                    if name == ".PKGINFO":
                        logging.debug(
                            "=> Skipping, this is expected to be different")
                        continue

                    # Get members
                    member_a = tar_a.getmember(name)
                    member_b = tar_b.getmember(name)
                    if member_a.type != member_b.type:
                        raise RuntimeError(
                            "Entry '" + name + "' has a different type!")

                    if member_a.isdir():
                        logging.debug("=> Skipping, this is directory")
                    elif member_a.isfile():
                        diff_files(tar_a, tar_b, member_a, member_b, name)
                    elif member_a.issym() or member_a.islnk():
                        if member_a.linkname == member_b.linkname:
                            logging.debug(
                                "=> Both link to " + member_a.linkname)
                        else:
                            raise RuntimeError(
                                "Link " + name + " has a different target!")
                    else:
                        raise RuntimeError(
                            "Can't diff '" + name + "', unsupported type!")
                except Exception as e:
                    logging.info("CHALLENGE FAILED for " + name + ":" + str(e))
                    success = False
            if not success:
                raise RuntimeError("Challenge failed (see errors above)")


def challenge(args, apk_path):
    # Parse buildinfo
    buildinfo_path = apk_path + ".buildinfo.json"
    if not os.path.exists(buildinfo_path):
        logging.info("NOTE: To create a .buildinfo.json file, use the"
                     " --buildinfo command while building: 'pmbootstrap build"
                     " --buildinfo <pkgname>'")
        raise RuntimeError("Missing file: " + buildinfo_path)
    with open(buildinfo_path) as handle:
        buildinfo = json.load(handle)

    # Parse and install all packages listed in versions
    versions = {}
    for package in buildinfo["versions"]:
        split = pmb.parse.other.package_split(package)
        pkgname = split["pkgname"]
        versions[pkgname] = split
    pmb.chroot.apk.install(args, versions.keys())

    # Verify the installed versions
    installed = pmb.chroot.apk.installed(args)
    for pkgname, split in versions.items():
        package_installed = installed[pkgname]["package"]
        package_buildinfo = split["package"]
        if package_installed != package_buildinfo:
            raise RuntimeError("Dependency " + pkgname + " version is different"
                               " (installed: " + package_installed + ","
                               " buildinfo: " + package_buildinfo + ")!")
    # Build the package
    repo_before = pmb.helpers.repo.files(args)
    pmb.build.package(args, buildinfo["pkgname"], buildinfo["arch"],
                      force=True)
    repo_diff = pmb.helpers.repo.diff(args, repo_before)

    # Diff the apk contents
    staging_path = os.path.abspath(os.path.dirname(apk_path) + "/../")
    for file in repo_diff:
        if file.endswith(".apk"):
            logging.info("Verify " + file)
            diff(
                args,
                staging_path +
                "/" +
                file,
                args.work +
                "/packages/" +
                file)

    # Output the changed files from the repository
    if args.output_repo_changes:
        with open(args.output_repo_changes, "w") as handler:
            for file in repo_diff:
                handler.write(file + "\n")
