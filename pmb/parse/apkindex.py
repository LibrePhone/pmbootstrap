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
import pmb.chroot.apk
import pmb.helpers.repo
import pmb.parse.version


def parse_next_block(args, path, lines, start):
    """
    Parse the next block in an APKINDEX.

    :param path: to the APKINDEX.tar.gz
    :param start: current index in lines, gets increased in this
                  function. Wrapped into a list, so it can be modified
                  "by reference". Example: [5]
    :param lines: all lines from the "APKINDEX" file inside the archive
    :returns: a dictionary with the following structure:
              { "arch": "noarch",
                "depends": ["busybox-extras", "lddtree", ... ],
                "pkgname": "postmarketos-mkinitfs",
                "provides": ["mkinitfs=0.0.1"],
                "version": "0.0.4-r10",
              }
    :returns: None, when there are no more blocks
    """

    # Parse until we hit an empty line or end of file
    ret = {}
    mapping = {
        "A": "arch",
        "P": "pkgname",
        "V": "version",
        "D": "depends",
        "p": "provides",
        "t": "timestamp"
    }
    end_of_block_found = False
    for i in range(start[0], len(lines)):
        # Check for empty line
        start[0] = i + 1
        line = lines[i]
        if not isinstance(line, str):
            line = line.decode()
        if line == "\n":
            end_of_block_found = True
            break

        # Parse keys from the mapping
        for letter, key in mapping.items():
            if line.startswith(letter + ":"):
                if key in ret:
                    raise RuntimeError(
                        "Key " + key + " (" + letter + ":) specified twice"
                        " in block: " + str(ret) + ", file: " + path)
                ret[key] = line[2:-1]

    # Format and return the block
    if end_of_block_found:
        # Check for required keys
        for key in ["pkgname", "version", "timestamp"]:
            if key not in ret:
                raise RuntimeError("Missing required key '" + key +
                                   "' in block " + str(ret) + ", file: " + path)

        # Format optional lists
        for key in ["provides", "depends"]:
            if key in ret and ret[key] != "":
                # Ignore all operators for now
                values = ret[key].split(" ")
                ret[key] = []
                for value in values:
                    if value.startswith("!"):
                        continue
                    for operator in [">", "=", "<"]:
                        if operator in value:
                            value = value.split(operator)[0]
                            break
                    ret[key].append(value)
            else:
                ret[key] = []
        return ret

    # No more blocks
    elif ret != {}:
        raise RuntimeError("Last block in " + path + " does not end"
                           " with a new line! Delete the file and"
                           " try again. Last block: " + str(ret))
    return None


def parse_add_block(path, strict, ret, block, pkgname=None):
    """
    Add one block to the return dictionary of parse().

    :param path: to the APKINDEX.tar.gz
    :param strict: When set to True, only allow one entry per pkgname.
                   In case there are two, raise an exception.
                   When set to False, and there are multiple entries
                   for one pkgname, it uses the latest one.
    :param ret: dictionary of all packages in the APKINDEX, that is
                getting built right now. This function will extend it.
    :param block: return value from parse_next_block().
    :param pkgname: defaults to the real pkgname, could be an alias
                    from the "provides" list.
    :param version: defaults to the real version, could be a value
                    from the "provides" list.
    """

    # Defaults
    if not pkgname:
        pkgname = block["pkgname"]

    # Handle duplicate entries
    if pkgname in ret:
        if strict:
            raise RuntimeError("Multiple blocks for " + pkgname +
                               " in " + path)
        # Ignore the block, if the block we already have has a higher
        # version
        version_old = ret[pkgname]["version"]
        version_new = block["version"]
        if pmb.parse.version.compare(version_old, version_new) == 1:
            return

    # Add it to the result set
    ret[pkgname] = block


def parse(args, path, strict=False):
    """
    Parse an APKINDEX.tar.gz file, and return its content as dictionary.

    :param strict: When set to True, only allow one entry per pkgname.
                   In case there are two, raise an exception.
                   When set to False, and there are multiple entries
                   for one pkgname, it uses the latest one.
    :returns: a dictionary with the following structure:
              { "postmarketos-mkinitfs":
                {
                  "pkgname": "postmarketos-mkinitfs"
                  "version": "0.0.4-r10",
                  "depends": ["busybox-extras", "lddtree", ...],
                  "provides": ["mkinitfs=0.0.1"]
                }, ...
              }
    """

    # Try to get a cached result first
    lastmod = os.path.getmtime(path)
    if path in args.cache["apkindex"]:
        cache = args.cache["apkindex"][path]
        if cache["lastmod"] == lastmod:
            return cache["ret"]

    # Read all lines
    if tarfile.is_tarfile(path):
        with tarfile.open(path, "r:gz") as tar:
            with tar.extractfile(tar.getmember("APKINDEX")) as handle:
                lines = handle.readlines()
    else:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()

    # Parse the whole APKINDEX file
    ret = {}
    start = [0]
    while True:
        block = parse_next_block(args, path, lines, start)
        if not block:
            break

        # Add the next package and all aliases
        parse_add_block(path, strict, ret, block)
        if "provides" in block:
            for alias in block["provides"]:
                parse_add_block(path, strict, ret, block, alias)

    # Update the cache
    args.cache["apkindex"][path] = {"lastmod": lastmod, "ret": ret}

    return ret


def clear_cache(args, path):
    logging.verbose("Clear APKINDEX cache for: " + path)
    if path in args.cache["apkindex"]:
        del args.cache["apkindex"][path]
    else:
        logging.verbose("Nothing to do, path was not in cache:" +
                        str(args.cache["apkindex"].keys()))


def read(args, package, path, must_exist=True):
    """
    Get information about a single package from an APKINDEX.tar.gz file.

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

    # Parse the APKINDEX
    apkindex = parse(args, path)
    if package not in apkindex:
        if must_exist:
            raise RuntimeError("Package '" + package +
                               "' not found in " + path)
        else:
            return None
    return apkindex[package]


def read_any_index(args, package, arch=None):
    """
    Get information about a single package from any APKINDEX.tar.gz.

    :param arch: defaults to native architecture
    :returns: the same format as read()
    """
    if not arch:
        arch = args.arch_native

    # Return first match
    for index in pmb.helpers.repo.apkindex_files(args, arch):
        index_data = read(args, package, index, False)
        if index_data:
            logging.verbose(package + ": found in " + index)
            return index_data

    logging.verbose(package + ": no match found in any APKINDEX.tar.gz!")
    return None
