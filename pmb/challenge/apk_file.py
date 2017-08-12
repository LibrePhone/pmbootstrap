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
import tarfile
import tempfile
import filecmp
import shutil


def contents_diff(tar_a, tar_b, member_a, member_b, name):
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


def contents_without_signature(tar, tar_name):
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


def apk(args, apk_a, apk_b, stop_after_first_error=False):
    with tarfile.open(apk_a, "r:gz") as tar_a:
        with tarfile.open(apk_b, "r:gz") as tar_b:
            # List of files must be the same
            list_a = contents_without_signature(tar_a, apk_a)
            list_b = contents_without_signature(tar_b, apk_b)
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
                            "=> Skipping: expected to be different")
                        continue

                    # Get members
                    member_a = tar_a.getmember(name)
                    member_b = tar_b.getmember(name)
                    if member_a.type != member_b.type:
                        logging.info("NOTE: " + name + " in " + apk_a + ":")
                        tar_a.list(members=[member_a])
                        logging.info("NOTE: " + name + " in " + apk_b + ":")
                        tar_b.list(members=[member_b])
                        raise RuntimeError(
                            "Entry '" + name + "' has a different type!")

                    if member_a.isdir():
                        logging.debug("=> Skipping: directory")
                    elif member_a.isfile():
                        contents_diff(tar_a, tar_b, member_a, member_b, name)
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
                    if stop_after_first_error:
                        raise
            if not success:
                raise RuntimeError("Challenge failed (see errors above)")
