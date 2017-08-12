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
import fnmatch


def format_function(name, body, remove_indent=4):
    """
    Format the body of a shell function passed to rewrite() below, so it fits
    the format of the original APKBUILD.
    """
    ret = ""
    lines = body.split("\n")
    for i in range(len(lines)):
        line = lines[i]
        if not line.strip():
            if not ret or i == len(lines) - 1:
                continue
        ret += line[remove_indent:] + "\n"
    return name + "() {\n" + ret + "}\n"


def rewrite(args, pkgname, path_original, fields={}, replace_pkgname=None,
            replace_functions={}, replace_simple={}, below_header=""):
    """
    Append a header to $WORK/aportgen/APKBUILD, delete maintainer/contributor
    lines (so they won't be bugged with issues regarding our generated aports),
    and add reference to the original aport.

    :param fields: key-value pairs of fields, that shall be changed in the
        APKBUILD. For example: {"pkgdesc": "my new package", "subpkgs": ""}
    :param replace_pkgname: When set, $pkgname gets replaced with that string in
        every line.
    :param replace_functions: Function names and new bodies, for example:
        {"build": "return 0"}
        The body can also be None (deletes the function)
    :param replace_simple: Lines, that fnmatch the pattern, get
        replaced/deleted. Example: {"*test*": "# test", "*mv test.bin*": None}
    :param below_header: String, that gets directly placed below the header.

    """
    # Header
    lines_new = [
        "# Automatically generated aport, do not edit!\n",
        "# Generator: pmbootstrap aportgen " + pkgname + "\n",
        "# Based on: " + path_original + "\n",
        "\n",
    ]
    for line in below_header.split("\n"):
        if not line[:8].strip():
            line = line[8:]
        lines_new += line.rstrip() + "\n"

    # Copy/modify lines, skip Maintainer/Contributor
    path = args.work + "/aportgen/APKBUILD"
    with open(path, "r+", encoding="utf-8") as handle:
        skip_in_func = False
        for line in handle.readlines():
            # Skip maintainer/contributor
            if line.startswith("# Maintainer") or line.startswith(
                    "# Contributor"):
                continue

            # Replace functions
            if skip_in_func:
                if line.startswith("}"):
                    skip_in_func = False
                continue
            else:
                for func, body in replace_functions.items():
                    if line.startswith(func + "() {"):
                        skip_in_func = True
                        if body:
                            lines_new += format_function(func, body)
                        break
                if skip_in_func:
                    continue

            # Replace fields
            for key, value in fields.items():
                if line.startswith(key + "="):
                    line = key + "=\"" + value + "\"\n"
                    break

            # Replace $pkgname
            if replace_pkgname and "$pkgname" in line:
                line = line.replace("$pkgname", replace_pkgname)

            # Replace simple
            for pattern, replacement in replace_simple.items():
                if fnmatch.fnmatch(line, pattern):
                    line = replacement
                    if replacement:
                        line += "\n"
                    break
            if line is None:
                continue

            lines_new.append(line)

        # Write back
        handle.seek(0)
        handle.write("".join(lines_new))
        handle.truncate()
