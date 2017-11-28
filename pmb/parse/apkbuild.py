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
import pmb.config


def replace_variables(apkbuild):
    """
    Replace a hardcoded list of variables inside the APKBUILD.
    """
    ret = apkbuild
    # _flavor: ${_device} (lineageos kernel packages)
    ret["_flavor"] = ret["_flavor"].replace("${_device}",
                                            ret["_device"])

    # pkgname: $_flavor
    ret["pkgname"] = ret["pkgname"].replace("${_flavor}", ret["_flavor"])

    # subpackages: $pkgname
    replaced = []
    for subpackage in ret["subpackages"]:
        replaced.append(subpackage.replace("$pkgname", ret["pkgname"]))
    ret["subpackages"] = replaced

    # makedepends: $makedepends_host, $makedepends_build, $_llvmver
    replaced = []
    for makedepend in ret["makedepends"]:
        if makedepend.startswith("$"):
            key = makedepend[1:]
            if key in ret:
                replaced += ret[key]
            else:
                raise RuntimeError("Could not resolve variable " +
                                   makedepend + " in APKBUILD of " +
                                   apkbuild["pkgname"])
        else:
            # replace in the middle of the string
            for var in ["_llvmver"]:
                makedepend = makedepend.replace("$" + var, ret[var])
            replaced += [makedepend]

    # Python: ${pkgname#py-}
    if ret["pkgname"].startswith("py-"):
        replacement = ret["pkgname"][3:]
        for var in ["depends", "makedepends", "subpackages"]:
            for i in range(len(ret[var])):
                ret[var][i] = ret[var][i].replace(
                    "${pkgname#py-}", replacement)

    ret["makedepends"] = replaced
    return ret


def cut_off_function_names(apkbuild):
    """
    For subpackages: only keep the subpackage name, without the internal
    function name, that tells how to build the subpackage.
    """
    sub = apkbuild["subpackages"]
    for i in range(len(sub)):
        sub[i] = sub[i].split(":", 1)[0]
    apkbuild["subpackages"] = sub
    return apkbuild


def apkbuild(args, path):
    """
    Parse relevant information out of the APKBUILD file. This is not meant
    to be perfect and catch every edge case (for that, a full shell parser
    would be necessary!). Instead, it should just work with the use-cases
    covered by pmbootstrap and not take too long.

    :param path: Full path to the APKBUILD
    :returns: Relevant variables from the APKBUILD. Arrays get returned as
        arrays.
    """
    # Try to get a cached result first (we assume, that the aports don't change
    # in one pmbootstrap call)
    if path in args.cache["apkbuild"]:
        return args.cache["apkbuild"][path]

    # Read the file and check line endings
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()
        if handle.newlines != '\n':
            raise RuntimeError("Wrong line endings in APKBUILD: " + path)

    # Parse all attributes from the config
    ret = {}
    for i in range(len(lines)):
        for attribute, options in pmb.config.apkbuild_attributes.items():
            if not lines[i].startswith(attribute + "="):
                continue

            # Extend the line value until we reach the ending quote sign
            line_value = lines[i][len(attribute + "="):-1]
            end_char = None
            if line_value.startswith("\""):
                end_char = "\""
            value = ""
            first_line = i
            while i < len(lines) - 1:
                value += line_value.replace("\"", "").strip()
                if not end_char:
                    break
                elif line_value.endswith(end_char):
                    # This check is needed to allow line break directly after opening quote
                    if i != first_line or line_value.count(end_char) > 1:
                        break
                value += " "
                i += 1
                line_value = lines[i][:-1]

            # Split up arrays, delete empty strings inside the list
            if options["array"]:
                if value:
                    value = list(filter(None, value.split(" ")))
                else:
                    value = []
            ret[attribute] = value

    # Add missing keys
    for attribute, options in pmb.config.apkbuild_attributes.items():
        if attribute not in ret:
            if options["array"]:
                ret[attribute] = []
            else:
                ret[attribute] = ""

    # Properly format values
    ret = replace_variables(ret)
    ret = cut_off_function_names(ret)

    # Sanity check: pkgname
    suffix = "/" + ret["pkgname"] + "/APKBUILD"
    if not os.path.realpath(path).endswith(suffix):
        logging.info("Folder: '" + os.path.dirname(path) + "'")
        logging.info("Pkgname: '" + ret["pkgname"] + "'")
        raise RuntimeError("The pkgname must be equal to the name of"
                           " the folder, that contains the APKBUILD!")

    # Sanity check: arch
    if not len(ret["arch"]):
        raise RuntimeError("Arch must not be empty: " + path)

    # Fill cache
    args.cache["apkbuild"][path] = ret
    return ret
