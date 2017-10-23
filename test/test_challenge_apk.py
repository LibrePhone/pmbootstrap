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
import tarfile

# Import from parent directory
sys.path.append(os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.challenge.apk_file
import pmb.config
import pmb.chroot.other
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


def test_apk_challenge_contents_diff(args):
    """
    Create two tar files, which contain a file with the same name.
    The content of that file is different.
    """
    # Tempfolder inside chroot for fake apk files
    temp_path = pmb.chroot.other.tempfolder(
        args, "/tmp/test_apk_challenge_contents_diff")
    temp_path_outside = args.work + "/chroot_native" + temp_path

    # First file
    name = "testfile"
    apk_a = temp_path_outside + "/a.apk"
    pmb.chroot.user(args, ["cp", "/etc/inittab", temp_path + "/" + name])
    pmb.chroot.user(args, ["tar", "-czf", "a.apk", name],
                    working_dir=temp_path)

    # Second file
    apk_b = temp_path_outside + "/b.apk"
    pmb.chroot.user(args, ["cp", "/etc/motd", temp_path + "/" + name])
    pmb.chroot.user(args, ["tar", "-czf", "b.apk", name],
                    working_dir=temp_path)

    # Compare OK
    with tarfile.open(apk_a, "r:gz") as tar_a:
        member_a = tar_a.getmember(name)
        pmb.challenge.apk_file.contents_diff(
            tar_a, tar_a, member_a, member_a, name)

        # Compare NOK
        with tarfile.open(apk_b, "r:gz") as tar_b:
            member_b = tar_b.getmember(name)
            with pytest.raises(RuntimeError) as e:
                pmb.challenge.apk_file.contents_diff(tar_a, tar_b, member_a,
                                                     member_b, name)
            assert str(e.value).endswith(" is different!")


def test_apk_challenge_contents_without_signature(args):
    # Tempfolder inside chroot for fake apk files
    temp_path = pmb.chroot.other.tempfolder(
        args, "/tmp/test_apk_challenge_nosig")
    temp_path_outside = args.work + "/chroot_native" + temp_path

    # Create three archives
    contents = {
        "no_sig.apk": ["other_file"],
        "one_sig.apk": [".SIGN.RSA.first", "other_file"],
        "two_sig.apk": [".SIGN.RSA.first", ".SIGN.RSA.second"],
    }
    for apk, files in contents.items():
        for file in files:
            pmb.chroot.user(args, ["touch", temp_path + "/" + file])
        pmb.chroot.user(args, ["tar", "-czf", apk] +
                        files, working_dir=temp_path)

    # No signature
    with tarfile.open(temp_path_outside + "/no_sig.apk", "r:gz") as tar:
        with pytest.raises(RuntimeError) as e:
            pmb.challenge.apk_file.contents_without_signature(tar, "a.apk")
        assert str(e.value).startswith("No signature file found")

    # One signature
    with tarfile.open(temp_path_outside + "/one_sig.apk", "r:gz") as tar:
        contents = pmb.challenge.apk_file.contents_without_signature(
            tar, "a.apk")
        assert contents == ["other_file"]

    # More than one signature
    with tarfile.open(temp_path_outside + "/two_sig.apk", "r:gz") as tar:
        with pytest.raises(RuntimeError) as e:
            pmb.challenge.apk_file.contents_without_signature(tar, "a.apk")
        assert str(e.value).startswith("More than one signature")


def test_apk_challenge_different_files_inside_archive(args):
    # Tempfolder inside chroot for fake apk files
    temp_path = pmb.chroot.other.tempfolder(args, "/tmp/test_apk_challenge")
    temp_path_outside = args.work + "/chroot_native" + temp_path

    # Create fake apks
    contents = {
        "a.apk": [".SIGN.RSA.first", "first_file", "second_file"],
        "b.apk": [".SIGN.RSA.second", "first_file"],
    }
    for apk, files in contents.items():
        for file in files:
            pmb.chroot.user(args, ["touch", temp_path + "/" + file])
        pmb.chroot.user(args, ["tar", "-czf", apk] +
                        files, working_dir=temp_path)

    # Challenge both files
    with pytest.raises(RuntimeError) as e:
        pmb.challenge.apk(args, temp_path_outside + "/a.apk",
                          temp_path_outside + "/b.apk")
    assert "do not contain the same file names" in str(e.value)


def test_apk_challenge_entry_has_a_different_type(args):
    # Tempfolder inside chroot for fake apk files
    temp_path = pmb.chroot.other.tempfolder(args, "/tmp/test_apk_challenge")
    temp_path_outside = args.work + "/chroot_native" + temp_path

    # Create fake apks
    contents = {
        "a.apk": [".SIGN.RSA.first", ".APKINDEX", "different_type"],
        "b.apk": [".SIGN.RSA.second", ".APKINDEX", "different_type"],
    }
    for apk, files in contents.items():
        for file in files:
            if file == "different_type" and apk == "b.apk":
                pmb.chroot.user(args, ["rm", temp_path + "/" + file])
                pmb.chroot.user(args, ["mkdir", temp_path + "/" + file])
            else:
                pmb.chroot.user(args, ["touch", temp_path + "/" + file])
        pmb.chroot.user(args, ["tar", "-czf", apk] +
                        files, working_dir=temp_path)

    # Exact error (with stop_after_first_error)
    with pytest.raises(RuntimeError) as e:
        pmb.challenge.apk(args, temp_path_outside + "/a.apk",
                          temp_path_outside + "/b.apk", stop_after_first_error=True)
    assert "has a different type!" in str(e.value)

    # Generic error
    with pytest.raises(RuntimeError) as e:
        pmb.challenge.apk(args, temp_path_outside + "/a.apk",
                          temp_path_outside + "/b.apk")
    assert "Challenge failed"


def test_apk_challenge_file_has_different_content(args):
    # Tempfolder inside chroot for fake apk files
    temp_path = pmb.chroot.other.tempfolder(args, "/tmp/test_apk_challenge")
    temp_path_outside = args.work + "/chroot_native" + temp_path

    # Create fake apks
    contents = {
        "a.apk": [".SIGN.RSA.first", ".APKINDEX", "different_content"],
        "b.apk": [".SIGN.RSA.second", ".APKINDEX", "different_content"],
    }
    for apk, files in contents.items():
        for file in files:
            if file == "different_content" and apk == "b.apk":
                pmb.chroot.user(
                    args, [
                        "cp", "/etc/hostname", temp_path + "/" + file])
            else:
                pmb.chroot.user(args, ["touch", temp_path + "/" + file])
        pmb.chroot.user(args, ["tar", "-czf", apk] +
                        files, working_dir=temp_path)

    # Exact error (with stop_after_first_error)
    with pytest.raises(RuntimeError) as e:
        pmb.challenge.apk(args, temp_path_outside + "/a.apk",
                          temp_path_outside + "/b.apk", stop_after_first_error=True)
    assert str(e.value).endswith("is different!")

    # Generic error
    with pytest.raises(RuntimeError) as e:
        pmb.challenge.apk(args, temp_path_outside + "/a.apk",
                          temp_path_outside + "/b.apk")
    assert "Challenge failed"


def test_apk_challenge_different_link_target(args):
    # Tempfolder inside chroot for fake apk files
    temp_path = pmb.chroot.other.tempfolder(args, "/tmp/test_apk_challenge")
    temp_path_outside = args.work + "/chroot_native" + temp_path

    # Create fake apks
    contents = {
        "a.apk": [".SIGN.RSA.first", ".APKINDEX", "link_same", "link_different"],
        "b.apk": [".SIGN.RSA.second", ".APKINDEX", "link_same", "link_different"],
    }
    for apk, files in contents.items():
        for file in files:
            if file.startswith("link_"):
                if file == "link_different" and apk == "b.apk":
                    pmb.chroot.user(args, ["ln", "-sf", "/different_target",
                                           temp_path + "/" + file])
                else:
                    pmb.chroot.user(args, ["ln", "-sf", "/some_link_target",
                                           temp_path + "/" + file])
            else:
                pmb.chroot.user(args, ["touch", temp_path + "/" + file])
        pmb.chroot.user(args, ["tar", "-czf", apk] +
                        files, working_dir=temp_path)

    # Exact error (with stop_after_first_error)
    with pytest.raises(RuntimeError) as e:
        pmb.challenge.apk(args, temp_path_outside + "/a.apk",
                          temp_path_outside + "/b.apk", stop_after_first_error=True)
    assert str(e.value).endswith("has a different target!")

    # Generic error
    with pytest.raises(RuntimeError) as e:
        pmb.challenge.apk(args, temp_path_outside + "/a.apk",
                          temp_path_outside + "/b.apk")
    assert "Challenge failed"


def test_apk_challenge_unsupported_type(args):
    # Tempfolder inside chroot for fake apk files
    temp_path = pmb.chroot.other.tempfolder(args, "/tmp/test_apk_challenge")
    temp_path_outside = args.work + "/chroot_native" + temp_path

    # Create fake apk with a FIFO (-> unsupported type)
    apk = "test.apk"
    content = [".SIGN.RSA.first", ".APKINDEX", "fifo"]
    for file in content:
        if file == "fifo":
            pmb.chroot.user(args, ["mkfifo", temp_path + "/" + file])
        else:
            pmb.chroot.user(args, ["touch", temp_path + "/" + file])
    pmb.chroot.user(args, ["tar", "-czf", apk] +
                    content, working_dir=temp_path)

    # Exact error (with stop_after_first_error)
    with pytest.raises(RuntimeError) as e:
        pmb.challenge.apk(args, temp_path_outside + "/test.apk",
                          temp_path_outside + "/test.apk", stop_after_first_error=True)
    assert str(e.value).endswith("unsupported type!")

    # Generic error
    with pytest.raises(RuntimeError) as e:
        pmb.challenge.apk(args, temp_path_outside + "/test.apk",
                          temp_path_outside + "/test.apk")
    assert "Challenge failed"
