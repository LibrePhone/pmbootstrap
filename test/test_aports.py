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
    Require "postmarketos-base" to be in the device APKBUILD's depends.
    """

    for path in glob.glob(args.aports + "/device/device-*/APKBUILD"):
        apkbuild = pmb.parse.apkbuild(args, path)
        if "postmarketos-base" not in apkbuild["depends"]:
            raise RuntimeError("Missing 'postmarketos-base' in depends of " +
                               path)
