"""
Copyright 2018 Oliver Smith

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
import pytest
import sys

# Import from parent directory
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.append(pmb_src)
import pmb.parse
import pmb.parse._apkbuild


@pytest.fixture
def args(request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_deviceinfo(args):
    """
    Parse all deviceinfo files. When no exception gets raised, we're good.
    """
    for folder in glob.glob(args.aports + "/device/device-*"):
        device = folder.split("-", 1)[1]
        print(device)
        pmb.parse.deviceinfo(args, device)


def test_aports_device(args):
    """
    Various tests performed on the /device/device-* aports.
    """
    for path in glob.glob(args.aports + "/device/device-*/APKBUILD"):
        apkbuild = pmb.parse.apkbuild(args, path)

        # Depends: Require "postmarketos-base"
        if "postmarketos-base" not in apkbuild["depends"]:
            raise RuntimeError("Missing 'postmarketos-base' in depends of " +
                               path)

        # Depends: Must not have firmware packages
        for depend in apkbuild["depends"]:
            if depend.startswith("firmware-") or depend == "linux-firmware":
                raise RuntimeError("Firmware package '" + depend + "' found in"
                                   " depends of " + path + ". These go into"
                                   " subpackages now, see"
                                   " <https://postmarketos.org/devicepkg>.")


def test_aports_device_kernel(args):
    """
    Verify the kernels specified in the device packages:
    * Kernel must not be in depends when kernels are in subpackages
    * Check if only one kernel is defined in depends
    * Validate kernel subpackage names
    """
    # Generate list of valid subpackages
    valid_subpackages = ["downstream"]
    for path in glob.glob(args.aports + "/main/linux-postmarketos-*"):
        suffix = os.path.basename(path)[len("linux-postmarketos-"):]
        valid_subpackages.append(suffix)

    # Iterate over device aports
    for path in glob.glob(args.aports + "/device/device-*/APKBUILD"):
        # Parse apkbuild and kernels from subpackages
        apkbuild = pmb.parse.apkbuild(args, path)
        device = apkbuild["pkgname"][len("device-"):]
        kernels_subpackages = pmb.parse._apkbuild.kernels(args, device)

        # Parse kernels from depends
        kernels_depends = []
        for depend in apkbuild["depends"]:
            if not depend.startswith("linux-"):
                continue
            kernels_depends.append(depend)

            # Kernel in subpackages *and* depends
            if kernels_subpackages:
                raise RuntimeError("Kernel package '" + depend + "' needs to"
                                   " be removed when using kernel" +
                                   " subpackages: " + path)

        # No kernel
        if not kernels_depends and not kernels_subpackages:
            raise RuntimeError("Device doesn't have a kernel in depends or"
                               " subpackages: " + path)

        # Multiple kernels in depends
        if len(kernels_depends) > 1:
            raise RuntimeError("Please use kernel subpackages instead of"
                               " multiple kernels in depends (see"
                               " <https://postmarketos.org/deviceinfo>): " +
                               path)

        # Verify subpackages
        if kernels_subpackages:
            for subpackage in kernels_subpackages:
                if subpackage not in valid_subpackages:
                    raise RuntimeError("Invalid kernel subpackage name '" +
                                       subpackage + "', valid: " +
                                       str(valid_subpackages))
