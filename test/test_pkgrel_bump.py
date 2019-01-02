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

"""
This file tests pmb.helper.pkgrel_bump
"""

import glob
import os
import pytest
import sys

# Import from parent directory
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, pmb_src)
import pmb.helpers.pkgrel_bump
import pmb.helpers.logging


@pytest.fixture
def args(request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def pmbootstrap(args, tmpdir, parameters, zero_exit=True):
    """
    Helper function for running pmbootstrap inside the fake work folder (created
    by setup() below) with the binary repo disabled and with the testdata
    configured as aports.

    :param parameters: what to pass to pmbootstrap, e.g. ["build", "testlib"]
    :param zero_exit: expect pmbootstrap to exit with 0 (no error)
    """
    # Run pmbootstrap
    aports = tmpdir + "/_aports"
    config = tmpdir + "/_pmbootstrap.cfg"

    try:
        pmb.helpers.run.user(args, ["./pmbootstrap.py", "--work=" + tmpdir,
                                    "--mirror-pmOS=", "--aports=" + aports,
                                    "--config=" + config] + parameters,
                             working_dir=pmb_src)

    # Verify that it exits as desired
    except Exception as exc:
        if zero_exit:
            raise RuntimeError("pmbootstrap failed") from exc
        else:
            return
    if not zero_exit:
        raise RuntimeError("Expected pmbootstrap to fail, but it did not!")


def setup_work(args, tmpdir):
    """
    Create fake work folder in tmpdir with everything symlinked except for the
    built packages. The aports testdata gets copied to the tempfolder as
    well, so it can be modified during testing.
    """
    # Clean the chroots, and initialize the build chroot in the native chroot.
    # We do this before creating the fake work folder, because then all packages
    # are still present.
    os.chdir(pmb_src)
    pmb.helpers.run.user(args, ["./pmbootstrap.py", "-y", "zap"])
    pmb.helpers.run.user(args, ["./pmbootstrap.py", "build_init"])
    pmb.helpers.run.user(args, ["./pmbootstrap.py", "shutdown"])

    # Link everything from work (except for "packages") to the tmpdir
    for path in glob.glob(args.work + "/*"):
        if os.path.basename(path) != "packages":
            pmb.helpers.run.user(args, ["ln", "-s", path, tmpdir + "/"])

    # Copy testdata and selected device aport
    for folder in ["device", "main"]:
        pmb.helpers.run.user(args, ["mkdir", "-p", args.aports, tmpdir +
                                    "/_aports/" + folder])
    pmb.helpers.run.user(args, ["cp", "-r", args.aports + "/device/device-" +
                                args.device, tmpdir + "/_aports/device"])
    for pkgname in ["testlib", "testapp", "testsubpkg"]:
        pmb.helpers.run.user(args, ["cp", "-r",
                                    "test/testdata/pkgrel_bump/aports/" + pkgname,
                                    tmpdir + "/_aports/main/" + pkgname])

    # Copy pmaports.cfg
    pmb.helpers.run.user(args, ["cp", args.aports + "/pmaports.cfg", tmpdir +
                                "/_aports"])

    # Empty packages folder
    pmb.helpers.run.user(args, ["mkdir", "-p", tmpdir + "/packages"])
    pmb.helpers.run.user(args, ["chmod", "777", tmpdir + "/packages"])

    # Copy over the pmbootstrap config
    pmb.helpers.run.user(args, ["cp", args.config, tmpdir +
                                "/_pmbootstrap.cfg"])


def verify_pkgrels(args, tmpdir, pkgrel_testlib, pkgrel_testapp,
                   pkgrel_testsubpkg):
    """
    Verify the pkgrels of the three test APKBUILDs ("testlib", "testapp",
    "testsubpkg").
    """
    args.cache["apkbuild"] = {}
    mapping = {"testlib": pkgrel_testlib,
               "testapp": pkgrel_testapp,
               "testsubpkg": pkgrel_testsubpkg}
    for pkgname, pkgrel in mapping.items():
        # APKBUILD path
        path = tmpdir + "/_aports/main/" + pkgname + "/APKBUILD"

        # Parse and verify
        apkbuild = pmb.parse.apkbuild(args, path)
        assert pkgrel == int(apkbuild["pkgrel"])


def test_pkgrel_bump_high_level(args, tmpdir):
    # Tempdir setup
    tmpdir = str(tmpdir)
    setup_work(args, tmpdir)

    # Let pkgrel_bump exit normally
    pmbootstrap(args, tmpdir, ["build", "testlib", "testapp", "testsubpkg"])
    pmbootstrap(args, tmpdir, ["pkgrel_bump", "--dry", "--auto"])
    verify_pkgrels(args, tmpdir, 0, 0, 0)

    # Increase soname (testlib soname changes with the pkgrel)
    pmbootstrap(args, tmpdir, ["pkgrel_bump", "testlib"])
    verify_pkgrels(args, tmpdir, 1, 0, 0)
    pmbootstrap(args, tmpdir, ["build", "testlib"])
    pmbootstrap(args, tmpdir, ["pkgrel_bump", "--dry", "--auto"])
    verify_pkgrels(args, tmpdir, 1, 0, 0)

    # Delete package with previous soname (--auto-dry exits with >0 now)
    pmb.helpers.run.root(args, ["rm", tmpdir + "/packages/" +
                                args.arch_native + "/testlib-1.0-r0.apk"])
    pmbootstrap(args, tmpdir, ["index"])
    pmbootstrap(args, tmpdir, ["pkgrel_bump", "--dry", "--auto"], False)
    verify_pkgrels(args, tmpdir, 1, 0, 0)

    # Bump pkgrel and build testapp/testsubpkg
    pmbootstrap(args, tmpdir, ["pkgrel_bump", "--auto"])
    verify_pkgrels(args, tmpdir, 1, 1, 1)
    pmbootstrap(args, tmpdir, ["build", "testapp", "testsubpkg"])

    # After rebuilding, pkgrel_bump --auto-dry exits with 0
    pmbootstrap(args, tmpdir, ["pkgrel_bump", "--dry", "--auto"])
    verify_pkgrels(args, tmpdir, 1, 1, 1)

    # Test running with specific package names
    pmbootstrap(args, tmpdir, ["pkgrel_bump", "invalid_package_name"], False)
    pmbootstrap(args, tmpdir, ["pkgrel_bump", "--dry", "testlib"], False)
    verify_pkgrels(args, tmpdir, 1, 1, 1)

    # Clean up
    pmbootstrap(args, tmpdir, ["shutdown"])
    pmb.helpers.run.root(args, ["rm", "-rf", tmpdir])
