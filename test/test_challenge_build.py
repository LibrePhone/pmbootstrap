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
import sys
import pytest

# Import from parent directory
sys.path.append(os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.build
import pmb.challenge.build
import pmb.config
import pmb.helpers.logging
import pmb.parse


@pytest.fixture
def args(request, tmpdir):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_challenge_build(args):
    # Build the "hello-world" package
    pkgname = "hello-world"
    pmb.build.package(args, pkgname, None, force=True, buildinfo=True)

    # Copy it to a temporary path
    aport = pmb.build.other.find_aport(args, "hello-world")
    apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
    version = apkbuild["pkgver"] + "-r" + apkbuild["pkgrel"]
    temp_path = pmb.chroot.other.tempfolder(args, "/tmp/test_challenge_build/" +
                                            args.arch_native)
    packages_path = "/home/pmos/packages/pmos/" + args.arch_native
    apk_path = packages_path + "/" + pkgname + "-" + version + ".apk"
    pmb.chroot.user(args, ["cp", apk_path, apk_path + ".buildinfo.json",
                           temp_path])

    # Change the timestamps of all files, so the changes file gets written
    # correctly, even if this testcase gets executed very fast
    pmb.chroot.user(args, ["touch", "-d", "2017-01-01",
                           packages_path + "/APKINDEX.tar.gz",
                           apk_path,
                           apk_path + ".buildinfo.json"])

    # Challenge, output changes into a file
    args.cache["built"] = {}
    setattr(args, "output_repo_changes", args.work + "/chroot_native/tmp/"
                  "test_challenge_build_output.txt")
    pmb.challenge.build(args, args.work + "/chroot_native/" + temp_path + "/" +
                        os.path.basename(apk_path))

    # Verify the output textfile
    with open(args.output_repo_changes, "r") as handle:
        lines = handle.readlines()
        assert lines == [args.arch_native + "/APKINDEX.tar.gz\n",
                         args.arch_native + "/" + pkgname + "-" + version + ".apk\n",
                         args.arch_native + "/" + pkgname + "-" + version + ".apk.buildinfo.json\n"]
