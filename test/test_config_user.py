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
import sys
import pytest

# Import from parent directory
sys.path.insert(0, os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.aportgen
import pmb.config
import pmb.helpers.frontend
import pmb.helpers.logging
import pmb.helpers.run


@pytest.fixture
def args(tmpdir, request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def change_config(monkeypatch, path_config, key, value):
    args = args_patched(monkeypatch, ["pmbootstrap.py", "-c", path_config, "config",
                                      key, value])
    pmb.helpers.frontend.config(args)


def args_patched(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", argv)
    return pmb.parse.arguments()


def test_config_user(args, tmpdir, monkeypatch):
    # Temporary paths
    tmpdir = str(tmpdir)
    path_work = tmpdir + "/work"
    path_config = tmpdir + "/pmbootstrap.cfg"

    # Generate default config (only uses tmpdir)
    cmd = pmb.helpers.run.flat_cmd(["./pmbootstrap.py",
                                    "-c", path_config,
                                    "-w", path_work,
                                    "--aports", args.aports,
                                    "init"])
    pmb.helpers.run.user(args, ["sh", "-c", "yes '' | " + cmd],
                         pmb.config.pmb_src)

    # Load and verify default config
    argv = ["pmbootstrap.py", "-c", path_config, "config"]
    args_default = args_patched(monkeypatch, argv)
    assert args_default.work == path_work

    # Modify jobs count
    change_config(monkeypatch, path_config, "jobs", "9000")
    assert args_patched(monkeypatch, argv).jobs == "9000"

    # Override jobs count via commandline (-j)
    argv_jobs = ["pmbootstrap.py", "-c", path_config, "-j", "1000", "config"]
    assert args_patched(monkeypatch, argv_jobs).jobs == "1000"

    # Override a config option with something that evaluates to false
    argv_empty = ["pmbootstrap.py", "-c", path_config, "-w", "",
                  "--details-to-stdout", "config"]
    assert args_patched(monkeypatch, argv_empty).work == ""
