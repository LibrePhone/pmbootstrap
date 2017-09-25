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
import pmb.build.other
import pmb.chroot.apk
import pmb.chroot.root
import pmb.helpers.run
import pmb.helpers.logging
import pmb.helpers.git


@pytest.fixture
def args(request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def temp_aports_repo(args):
    # Temp folder
    temp = "/tmp/test_aport_in_sync_with_git"
    temp_outside = args.work + "/chroot_native" + temp
    if os.path.exists(temp_outside):
        pmb.chroot.root(args, ["rm", "-rf", temp])
    pmb.chroot.user(args, ["mkdir", temp])

    # Create fake "aports" repo
    # For this test to work, we need a git repository cloned from a real upstream
    # location. It does not work, when cloned from the same file system. The
    # aports_upstream repo also gets used in test_aportgen.py, so we use that.
    pmb.chroot.apk.install(args, ["git"])
    pmb.helpers.git.clone(args, "aports_upstream")
    pmb.chroot.user(args, ["cp", "-r", "/home/user/git/aports_upstream",
                           temp + "/aports"])

    # Configure git
    pmb.chroot.user(args, ["git", "config", "user.email", "user@localhost"],
                    working_dir=temp + "/aports")
    pmb.chroot.user(args, ["git", "config", "user.name", "User"],
                    working_dir=temp + "/aports")

    # Update args.aports
    setattr(args, "aports", temp_outside + "/aports")
    return temp + "/aports"


def out_of_sync_files(args):
    """
    Clear the cache again (because when running pmbootstrap normally, we assume,
    that the contents of the aports folder does not change during one run) and
    return the files out of sync for the hello-world package.
    """
    args.cache["aports_files_out_of_sync_with_git"] = None
    return pmb.build.other.aports_files_out_of_sync_with_git(args,
                                                             "alpine-base")


def test_aport_in_sync_with_git(args):
    aports = temp_aports_repo(args)
    ret_in_sync = []
    ret_out_of_sync = [os.path.realpath(args.aports + "/main/alpine-base/APKBUILD")]

    # In sync (no files changed)
    assert out_of_sync_files(args) == ret_in_sync

    # Out of sync: untracked files
    pmb.chroot.user(args, ["sh -c 'echo test >> " + aports +
                           "/main/alpine-base/APKBUILD'"])
    assert out_of_sync_files(args) == ret_out_of_sync

    # Out of sync: tracked files
    pmb.chroot.user(args, ["git", "add", aports + "/main/alpine-base/APKBUILD"],
                    working_dir=aports)
    assert out_of_sync_files(args) == ret_out_of_sync

    # Out of sync: comitted files
    pmb.chroot.user(args, ["git", "commit", "-m", "test"], working_dir=aports)
    assert out_of_sync_files(args) == ret_out_of_sync

    # In sync: undo the commit and check out a new branch
    pmb.chroot.user(args, ["git", "reset", "--hard", "origin/master"],
                    working_dir=aports)
    pmb.chroot.user(args, ["git", "checkout", "-b", "pmbootstrap-testbranch"],
                    working_dir=aports)
    assert out_of_sync_files(args) == ret_in_sync

    # In sync: not a git repository
    pmb.chroot.user(args, ["rm", "-rf", aports + "/.git"])
    assert out_of_sync_files(args) == ret_in_sync

    # TODO:
    # - reinstall git, but rm .git, check again
    # - remove temporary folder


def test_ambigious_argument(args):
    """
    Testcase for #151, forces "fatal: ambiguous argument" in git.
    See also: https://stackoverflow.com/a/17639471
    """

    # Delete origin/HEAD
    aports = temp_aports_repo(args)
    pmb.chroot.user(args, ["git", "update-ref", "-d", "refs/remotes/origin/HEAD"],
                    working_dir=aports)

    # Check for exception
    with pytest.raises(RuntimeError) as e:
        out_of_sync_files(args)
    assert "'origin/HEAD' reference" in str(e.value)
