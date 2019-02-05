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
import os
import logging
import pmb.config
import pmb.parse.version


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

    # subpackages, *depends*: $pkgname
    for key in ["subpackages", "depends", "makedepends", "makedepends_host",
                "makedepends_build"]:
        replaced = []
        for subpackage in ret[key]:
            replaced.append(subpackage.replace("$pkgname", ret["pkgname"]))
        ret[key] = replaced

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


def function_body(path, func):
    """
    Get the body of a function in an APKBUILD.

    :param path: full path to the APKBUILD
    :param func: name of function to get the body of.
    :returns: function body in an array of strings.
    """
    func_body = []
    in_func = False
    lines = read_file(path)
    for line in lines:
        if in_func:
            if line.startswith("}"):
                in_func = False
                break
            func_body.append(line)
            continue
        else:
            if line.startswith(func + "() {"):
                in_func = True
                continue
    return func_body


def read_file(path):
    """
    Read an APKBUILD file

    :param path: full path to the APKBUILD
    :returns: contents of an APKBUILD as a list of strings
    """
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()
        if handle.newlines != '\n':
            raise RuntimeError("Wrong line endings in APKBUILD: " + path)
    return lines


def apkbuild(args, path, check_pkgver=True, check_pkgname=True):
    """
    Parse relevant information out of the APKBUILD file. This is not meant
    to be perfect and catch every edge case (for that, a full shell parser
    would be necessary!). Instead, it should just work with the use-cases
    covered by pmbootstrap and not take too long.
    Run 'pmbootstrap apkbuild_parse hello-world' for a full output example.

    :param path: full path to the APKBUILD
    :param check_pkgver: verify that the pkgver is valid.
    :param check_pkgname: the pkgname must match the name of the aport folder
    :returns: relevant variables from the APKBUILD. Arrays get returned as
              arrays.
    """
    # Try to get a cached result first (we assume, that the aports don't change
    # in one pmbootstrap call)
    if path in args.cache["apkbuild"]:
        return args.cache["apkbuild"][path]

    # Read the file and check line endings
    lines = read_file(path)

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
    if check_pkgname:
        if not os.path.realpath(path).endswith(suffix):
            logging.info("Folder: '" + os.path.dirname(path) + "'")
            logging.info("Pkgname: '" + ret["pkgname"] + "'")
            raise RuntimeError("The pkgname must be equal to the name of"
                               " the folder, that contains the APKBUILD!")

    # Sanity check: arch
    if not len(ret["arch"]):
        raise RuntimeError("Arch must not be empty: " + path)

    # Sanity check: pkgver
    if check_pkgver:
        if "-r" in ret["pkgver"] or not pmb.parse.version.validate(ret["pkgver"]):
            logging.info("NOTE: Valid pkgvers are described here:")
            logging.info("<https://wiki.alpinelinux.org/wiki/APKBUILD_Reference#pkgver>")
            raise RuntimeError("Invalid pkgver '" + ret["pkgver"] +
                               "' in APKBUILD: " + path)

    # Fill cache
    args.cache["apkbuild"][path] = ret
    return ret


def subpkgdesc(path, function):
    """
    Get the pkgdesc of a subpackage in an APKBUILD.

    :param path: to the APKBUILD file
    :param function: name of the subpackage (e.g. "nonfree_userland")
    :returns: the subpackage's pkgdesc
    """
    # Read all lines
    lines = read_file(path)

    # Prefixes
    prefix_function = function + "() {"
    prefix_pkgdesc = "\tpkgdesc=\""

    # Find the pkgdesc
    in_function = False
    for line in lines:
        if in_function:
            if line.startswith(prefix_pkgdesc):
                return line[len(prefix_pkgdesc):-2]
        elif line.startswith(prefix_function):
            in_function = True

    # Failure
    if not in_function:
        raise RuntimeError("Could not find subpackage function, no line starts"
                           " with '" + prefix_function + "' in " + path)
    raise RuntimeError("Could not find pkgdesc of subpackage function '" +
                       function + "' (spaces used instead of tabs?) in " +
                       path)


def kernels(args, device):
    """
    Get the possible kernels from a device-* APKBUILD.

    :param device: the device name, e.g. "lg-mako"
    :returns: None when the kernel is hardcoded in depends
    :returns: kernel types and their description (as read from the subpackages)
              possible types: "downstream", "stable", "mainline"
              example: {"mainline": "Mainline description",
                        "downstream": "Downstream description"}
    """
    # Read the APKBUILD
    apkbuild_path = args.aports + "/device/device-" + device + "/APKBUILD"
    if not os.path.exists(apkbuild_path):
        return None
    subpackages = apkbuild(args, apkbuild_path)["subpackages"]

    # Read kernels from subpackages
    ret = {}
    subpackage_prefix = "device-" + device + "-kernel-"
    for subpackage in subpackages:
        if not subpackage.startswith(subpackage_prefix):
            continue
        name = subpackage[len(subpackage_prefix):]
        func = "kernel_" + name
        desc = pmb.parse._apkbuild.subpkgdesc(apkbuild_path, func)
        ret[name] = desc

    # Return
    if ret:
        return ret
    return None
