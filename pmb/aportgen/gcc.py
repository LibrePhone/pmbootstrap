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
import pmb.helpers.run
import pmb.aportgen.core


def generate(args, pkgname):
    # Copy original aport
    arch = pkgname.split("-")[1]
    path_original = "main/gcc"
    upstream = (args.work + "/cache_git/aports_upstream/" + path_original)
    pmb.helpers.run.user(args, ["cp", "-r", upstream, args.work + "/aportgen"])

    # Rewrite APKBUILD
    fields = {
        "pkgname": pkgname,
        "pkgdesc": "Stage2 cross-compiler for " + arch,
        "depends": "isl binutils-" + arch,
        "makedepends_build": "gcc g++ paxmark bison flex texinfo gawk zip gmp-dev mpfr-dev mpc1-dev zlib-dev",
        "makedepends_host": "linux-headers gmp-dev mpfr-dev mpc1-dev isl-dev zlib-dev musl-dev-" + arch + " binutils-" + arch,
        "subpackages": "g++-" + arch + ":gpp",

        "LIBGOMP": "false",
        "LIBGCC": "false",
        "LIBATOMIC": "false",
        "LIBITM": "false",
    }

    below_header = "CTARGET_ARCH=" + arch + """
        CTARGET="$(arch_to_hostspec ${CTARGET_ARCH})"
        CBUILDROOT="/usr/$CTARGET"
        LANG_OBJC=false
        LANG_JAVA=false
        LANG_GO=false
        LANG_FORTRAN=false
        LANG_ADA=false
        options="!strip !tracedeps"
    """

    replace_simple = {
        # Do not package libstdc++, do not add "g++-$ARCH" here (already
        # did that explicitly in the subpackages variable above, so
        # pmbootstrap picks it up properly).
        '*subpackages="$subpackages libstdc++:libcxx:*': None,

        # libstdc++.a is not reproducible by default (.a files are archives of
        # object files, and these object files are inside the .a file in a random
        # order!). The best way would be to patch this upstream in gcc, but for now
        # we repackage the .a files to make sure, that they are reproducible.
        '*package() {*': """package() {
            # Repack the *.a files to be reproducible (see #64)
            _temp="$_builddir"/_reproducible-patch
            cd "$_builddir"
            for f in $(find -name '*.a'); do
                # Copy to a temporary folder
                echo "Repack $f to be reproducible"
                mkdir -p "$_temp"
                cd "$_temp"
                cp "$_builddir"/"$f" .

                # Repack with a sorted file order
                ar x *.a
                rm *.a
                ar r sorted.a $(find -name '*.o' | sort)

                # Copy back and clean up
                cp -v sorted.a "$_builddir"/"$f"
                cd ..
                rm -r "$_temp"
            done"""
    }

    pmb.aportgen.core.rewrite(
        args,
        pkgname,
        path_original,
        fields,
        replace_simple=replace_simple,
        below_header=below_header)
