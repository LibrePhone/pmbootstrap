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


def test_questions(args, monkeypatch, tmpdir):
    #
    # PREPARATION
    #

    # Use prepared answers
    def fake_ask(args, question="Continue?", choices=["y", "n"], default="n",
                 lowercase_answer=True, validation_regex=None):
        answer = answers.pop(0)
        logging.info("pmb.helpers.cli.ask: fake answer: " + answer)
        return answer
    monkeypatch.setattr(pmb.helpers.cli, "ask", fake_ask)

    # Do not generate aports
    def fake_generate(args, pkgname):
        return
    monkeypatch.setattr(pmb.aportgen, "generate", fake_generate)

    # Self-test
    answers = ["first", "second"]
    assert pmb.helpers.cli.ask(args) == "first"
    assert pmb.helpers.cli.ask(args) == "second"
    assert len(answers) == 0

    #
    # SIMPLE QUESTIONS
    #

    # Booleans
    functions = [pmb.aportgen.device.ask_for_keyboard,
                 pmb.aportgen.device.ask_for_external_storage]
    for func in functions:
        answers = ["y", "n"]
        assert func(args) is True
        assert func(args) is False

    # Strings
    functions = [pmb.aportgen.device.ask_for_manufacturer,
                 pmb.aportgen.device.ask_for_name]
    for func in functions:
        answers = ["Simple string answer"]
        assert func(args) == "Simple string answer"

    #
    # QUESTIONS WITH ANSWER VERIFICATION
    #

    # Architecture
    answers = ["invalid_arch", "aarch64"]
    assert pmb.aportgen.device.ask_for_architecture(args) == "aarch64"

    # Device
    func = pmb.config.init.ask_for_device
    answers = ["lg-mako"]
    assert func(args) == ("lg-mako", True)

    answers = ["whoops-typo", "n", "lg-mako"]
    assert func(args) == ("lg-mako", True)

    answers = ["new-device", "y"]
    assert func(args) == ("new-device", False)

    # Flash methods
    func = pmb.aportgen.device.ask_for_flash_method
    answers = ["invalid_flash_method", "fastboot"]
    assert func(args) == "fastboot"

    answers = ["0xffff"]
    assert func(args) == "0xffff"

    answers = ["heimdall", "invalid_type", "isorec"]
    assert func(args) == "heimdall-isorec"

    answers = ["heimdall", "bootimg"]
    assert func(args) == "heimdall-bootimg"

    # Keymaps
    func = pmb.config.init.ask_for_keymaps
    answers = ["invalid_keymap", "us/rx51_us"]
    assert func(args, "nokia-rx51") == "us/rx51_us"
    assert func(args, "lg-mako") == ""

    # UI
    answers = ["invalid_UI", "weston"]
    assert pmb.config.init.ask_for_ui(args) == "weston"

    # Work path
    tmpdir = str(tmpdir)
    answers = ["/dev/null", tmpdir]
    assert pmb.config.init.ask_for_work_path(args) == tmpdir
