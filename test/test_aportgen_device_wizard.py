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
import pytest
import sys

# Import from parent directory
sys.path.append(os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.aportgen
import pmb.config
import pmb.helpers.logging
import pmb.parse


@pytest.fixture
def args(tmpdir, request):
    sys.argv = ["pmbootstrap.py", "build", "-i", "device-testsuite-testdevice"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)

    # Fake aports folder):
    tmpdir = str(tmpdir)
    setattr(args, "_aports_real", args.aports)
    args.aports = tmpdir
    pmb.helpers.run.user(args, ["mkdir", "-p", tmpdir + "/device"])

    # Copy the linux-lg-mako aport (we currently copy patches from there)
    path_mako = args._aports_real + "/device/linux-lg-mako"
    pmb.helpers.run.user(args, ["cp", "-r", path_mako, tmpdir + "/device"])
    return args


def generate(args, monkeypatch, answers):
    """
    Generate the device-new-device and linux-new-device aports (with a patched pmb.helpers.cli()).

    :returns: (deviceinfo, apkbuild, apkbuild_linux) - the parsed dictionaries
              of the created files, as returned by pmb.parse.apkbuild() and
              pmb.parse.deviceinfo().
    """
    # Patched function
    def fake_ask(args, question="Continue?", choices=["y", "n"], default="n",
                 lowercase_answer=True, validation_regex=None):
        for substr, answer in answers.items():
            if substr in question:
                logging.info(question + ": " + answer)
                # raise RuntimeError("test>" + answer)
                return answer
        raise RuntimeError("This testcase didn't expect the question '" +
                           question + "', please add it to the mapping.")

    # Generate the aports
    monkeypatch.setattr(pmb.helpers.cli, "ask", fake_ask)
    pmb.aportgen.generate(args, "device-testsuite-testdevice")
    pmb.aportgen.generate(args, "linux-testsuite-testdevice")
    monkeypatch.undo()

    # Parse the deviceinfo and apkbuilds
    args.cache["apkbuild"] = {}
    apkbuild_path = (args.aports + "/device/device-testsuite-testdevice/"
                     "APKBUILD")
    apkbuild_path_linux = (args.aports + "/device/"
                           "linux-testsuite-testdevice/APKBUILD")
    apkbuild = pmb.parse.apkbuild(args, apkbuild_path)
    apkbuild_linux = pmb.parse.apkbuild(args, apkbuild_path_linux)
    deviceinfo = pmb.parse.deviceinfo(args, "testsuite-testdevice")
    return (deviceinfo, apkbuild, apkbuild_linux)


def test_aportgen_device_wizard(args, monkeypatch):
    """
    Generate a device-testsuite-testdevice and linux-testsuite-testdevice
    package multiple times and check if the output is correct. Also build the
    device package once.
    """
    # Answers to interactive questions
    answers = {
        "Device architecture": "armhf",
        "external storage": "y",
        "hardware keyboard": "n",
        "Flash method": "heimdall",
        "Manufacturer": "Testsuite",
        "Name": "Testsuite Testdevice",
        "Type": "isorec",
    }

    # First run
    deviceinfo, apkbuild, apkbuild_linux = generate(args, monkeypatch, answers)
    assert apkbuild["pkgname"] == "device-testsuite-testdevice"
    assert apkbuild["pkgdesc"] == "Testsuite Testsuite Testdevice"
    assert apkbuild["depends"] == ["linux-testsuite-testdevice"]

    assert apkbuild_linux["pkgname"] == "linux-testsuite-testdevice"
    assert apkbuild_linux["pkgdesc"] == "Testsuite Testsuite Testdevice kernel fork"
    assert apkbuild_linux["arch"] == ["armhf"]
    assert apkbuild_linux["_flavor"] == "testsuite-testdevice"

    assert deviceinfo["name"] == "Testsuite Testdevice"
    assert deviceinfo["manufacturer"] == "Testsuite"
    assert deviceinfo["arch"] == "armhf"
    assert deviceinfo["keyboard"] == "false"
    assert deviceinfo["external_disk"] == "true"
    assert deviceinfo["flash_methods"] == "heimdall-isorec"
    assert deviceinfo["generate_bootimg"] == ""
    assert deviceinfo["generate_legacy_uboot_initfs"] == ""

    # Build the device package
    pkgname = "device-testsuite-testdevice"
    pmb.build.checksum(args, pkgname)
    pmb.build.package(args, pkgname, "x86_64", force=True)

    # Abort on overwrite confirmation
    answers["overwrite"] = "n"
    with pytest.raises(RuntimeError) as e:
        deviceinfo, apkbuild, apkbuild_linux = generate(args, monkeypatch,
                                                        answers)
    assert "Aborted." in str(e.value)

    # fastboot (mkbootimg)
    answers["overwrite"] = "y"
    answers["Flash method"] = "fastboot"
    answers["Path"] = ""
    deviceinfo, apkbuild, apkbuild_linux = generate(args, monkeypatch, answers)
    assert apkbuild["depends"] == ["linux-testsuite-testdevice", "mkbootimg"]
    assert deviceinfo["flash_methods"] == answers["Flash method"]
    assert deviceinfo["generate_bootimg"] == "true"

    # 0xffff (legacy uboot initfs)
    answers["Flash method"] = "0xffff"
    deviceinfo, apkbuild, apkbuild_linux = generate(args, monkeypatch, answers)
    assert apkbuild["depends"] == ["linux-testsuite-testdevice", "uboot-tools"]
    assert deviceinfo["generate_legacy_uboot_initfs"] == "true"
