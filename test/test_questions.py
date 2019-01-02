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
import logging
import os
import pytest
import sys

# Import from parent directory
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, pmb_src)
import pmb.aportgen.device
import pmb.config
import pmb.config.init
import pmb.helpers.logging


@pytest.fixture
def args(tmpdir, request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "init"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def fake_answers(monkeypatch, answers):
    """
    Patch pmb.helpers.cli.ask() function to return defined answers instead of
    asking the user for an answer.

    :param answers: list of answer strings, e.g. ["y", "n", "invalid-device"].
                    In this example, the first question is answered with "y",
                    the second question with "n" and so on.
    """
    def fake_ask(args, question="Continue?", choices=["y", "n"], default="n",
                 lowercase_answer=True, validation_regex=None):
        answer = answers.pop(0)
        logging.info("pmb.helpers.cli.ask() fake answer: " + answer)
        return answer
    monkeypatch.setattr(pmb.helpers.cli, "ask", fake_ask)


def test_fake_answers_selftest(monkeypatch):
    fake_answers(monkeypatch, ["first", "second"])
    assert pmb.helpers.cli.ask(args) == "first"
    assert pmb.helpers.cli.ask(args) == "second"


def test_questions_booleans(args, monkeypatch):
    functions = [pmb.aportgen.device.ask_for_keyboard,
                 pmb.aportgen.device.ask_for_external_storage]
    for func in functions:
        fake_answers(monkeypatch, ["y", "n"])
        assert func(args) is True
        assert func(args) is False


def test_questions_strings(args, monkeypatch):
    functions = [pmb.aportgen.device.ask_for_manufacturer]
    for func in functions:
        fake_answers(monkeypatch, ["Simple string answer"])
        assert func(args) == "Simple string answer"


def test_questions_name(args, monkeypatch):
    func = pmb.aportgen.device.ask_for_name

    # Manufacturer should get added automatically, but not twice
    fake_answers(monkeypatch, ["Amazon Thor"])
    assert func(args, "Amazon") == "Amazon Thor"
    fake_answers(monkeypatch, ["Thor"])
    assert func(args, "Amazon") == "Amazon Thor"

    # Don't add the manufacturer when it starts with "Google"
    fake_answers(monkeypatch, ["Google Nexus 12345"])
    assert func(args, "Amazon") == "Google Nexus 12345"


def test_questions_arch(args, monkeypatch):
    fake_answers(monkeypatch, ["invalid_arch", "aarch64"])
    assert pmb.aportgen.device.ask_for_architecture(args) == "aarch64"


def test_questions_bootimg(args, monkeypatch):
    func = pmb.aportgen.device.ask_for_bootimg
    fake_answers(monkeypatch, ["invalid_path", ""])
    assert func(args) is None

    bootimg_path = pmb_src + "/test/testdata/bootimg/normal-boot.img"
    fake_answers(monkeypatch, [bootimg_path])
    output = {"base": "0x80000000",
              "kernel_offset": "0x00008000",
              "ramdisk_offset": "0x04000000",
              "second_offset": "0x00f00000",
              "tags_offset": "0x0e000000",
              "pagesize": "2048",
              "cmdline": "bootopt=64S3,32S1,32S1",
              "qcdt": "false"}
    assert func(args) == output


def test_questions_device(args, monkeypatch):
    # Prepare args
    args.aports = pmb_src + "/test/testdata/init_questions_device/aports"
    args.device = "lg-mako"
    args.nonfree_firmware = True
    args.nonfree_userland = False
    args.kernel = "downstream"

    # Do not generate aports
    def fake_generate(args, pkgname):
        return
    monkeypatch.setattr(pmb.aportgen, "generate", fake_generate)

    # Existing device (without non-free components so we have defaults there)
    func = pmb.config.init.ask_for_device
    nonfree = {"firmware": True, "userland": False}
    fake_answers(monkeypatch, ["lg-mako"])
    kernel = args.kernel
    assert func(args) == ("lg-mako", True, kernel, nonfree)

    # Non-existing device, go back, existing device
    fake_answers(monkeypatch, ["whoops-typo", "n", "lg-mako"])
    assert func(args) == ("lg-mako", True, kernel, nonfree)

    # New device
    fake_answers(monkeypatch, ["new-device", "y"])
    assert func(args) == ("new-device", False, kernel, nonfree)


def test_questions_device_kernel(args, monkeypatch):
    # Prepare args
    args.aports = pmb_src + "/test/testdata/init_questions_device/aports"
    args.kernel = "downstream"

    # Kernel hardcoded in depends
    func = pmb.config.init.ask_for_device_kernel
    device = "lg-mako"
    assert func(args, device) == args.kernel

    # Choose "mainline"
    device = "sony-amami"
    fake_answers(monkeypatch, ["mainline"])
    assert func(args, device) == "mainline"

    # Choose "downstream"
    fake_answers(monkeypatch, ["downstream"])
    assert func(args, device) == "downstream"


def test_questions_device_nonfree(args, monkeypatch):
    # Prepare args
    args.aports = pmb_src + "/test/testdata/init_questions_device/aports"
    args.nonfree_firmware = False
    args.nonfree_userland = False

    # APKBUILD with firmware and userland (all yes)
    func = pmb.config.init.ask_for_device_nonfree
    device = "nonfree-firmware-and-userland"
    fake_answers(monkeypatch, ["y", "y"])
    nonfree = {"firmware": True, "userland": True}
    assert func(args, device) == nonfree

    # APKBUILD with firmware and userland (all no)
    fake_answers(monkeypatch, ["n", "n"])
    nonfree = {"firmware": False, "userland": False}
    assert func(args, device) == nonfree

    # APKBUILD with firmware only
    func = pmb.config.init.ask_for_device_nonfree
    device = "nonfree-firmware"
    fake_answers(monkeypatch, ["y"])
    nonfree = {"firmware": True, "userland": False}
    assert func(args, device) == nonfree

    # APKBUILD with userland only
    func = pmb.config.init.ask_for_device_nonfree
    device = "nonfree-userland"
    fake_answers(monkeypatch, ["y"])
    nonfree = {"firmware": False, "userland": True}
    assert func(args, device) == nonfree


def test_questions_flash_methods(args, monkeypatch):
    func = pmb.aportgen.device.ask_for_flash_method
    fake_answers(monkeypatch, ["invalid_flash_method", "fastboot"])
    assert func(args) == "fastboot"

    fake_answers(monkeypatch, ["0xffff"])
    assert func(args) == "0xffff"

    fake_answers(monkeypatch, ["heimdall", "invalid_type", "isorec"])
    assert func(args) == "heimdall-isorec"

    fake_answers(monkeypatch, ["heimdall", "bootimg"])
    assert func(args) == "heimdall-bootimg"


def test_questions_keymaps(args, monkeypatch):
    func = pmb.config.init.ask_for_keymaps
    fake_answers(monkeypatch, ["invalid_keymap", "us/rx51_us"])
    assert func(args, "nokia-n900") == "us/rx51_us"
    assert func(args, "lg-mako") == ""


def test_questions_qemu_native_mesa(args, monkeypatch):
    func = pmb.config.init.ask_for_qemu_native_mesa_driver
    fake_answers(monkeypatch, ["invalid_driver", "dri-swrast"])
    assert func(args, "qemu-amd64", "x86_64") == "dri-swrast"
    assert func(args, "qemu-aarch64", "x86_64") is None


def test_questions_ui(args, monkeypatch):
    fake_answers(monkeypatch, ["invalid_UI", "weston"])
    assert pmb.config.init.ask_for_ui(args) == "weston"


def test_questions_work_path(args, monkeypatch, tmpdir):
    # Existing paths (triggering various errors)
    func = pmb.config.init.ask_for_work_path
    tmpdir = str(tmpdir)
    fake_answers(monkeypatch, ["/dev/null", os.path.dirname(__file__),
                               pmb.config.pmb_src, tmpdir])
    assert func(args) == (tmpdir, True)

    # Non-existing path
    work = tmpdir + "/non_existing_subfolder"
    fake_answers(monkeypatch, [work])
    assert func(args) == (work, False)


def test_questions_build_options(args, monkeypatch):
    func = pmb.config.init.ask_for_build_options
    cfg = {"pmbootstrap": {}}

    # Skip changing anything
    fake_answers(monkeypatch, ["n"])
    func(args, cfg)
    assert cfg == {"pmbootstrap": {}}

    # Answer everything
    fake_answers(monkeypatch, ["y", "5", "2G", "n"])
    func(args, cfg)
    assert cfg == {"pmbootstrap": {"jobs": "5",
                                   "ccache_size": "2G"}}


def test_questions_hostname(args, monkeypatch):
    func = pmb.config.init.ask_for_hostname
    device = "test-device"

    # Valid hostname
    fake_answers(monkeypatch, ["valid"])
    assert func(args, device) == "valid"

    # Hostname too long ("aaaaa...")
    fake_answers(monkeypatch, ["a" * 64, "a" * 63])
    assert func(args, device) == "a" * 63

    # Fail the regex
    fake_answers(monkeypatch, ["$invalid", "valid"])
    assert func(args, device) == "valid"

    # Begins or ends with minus
    fake_answers(monkeypatch, ["-invalid", "invalid-", "valid"])
    assert func(args, device) == "valid"

    # Device name: empty string
    fake_answers(monkeypatch, [device])
    assert func(args, device) == ""
