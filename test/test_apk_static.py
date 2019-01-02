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
import tarfile
import glob
import pytest

# Import from parent directory
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, pmb_src)
import pmb.chroot.apk_static
import pmb.config
import pmb.parse.apkindex
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


def test_read_signature_info(args):
    # Tempfolder inside chroot for fake apk files
    tmp_path = "/tmp/test_read_signature_info"
    tmp_path_outside = args.work + "/chroot_native" + tmp_path
    if os.path.exists(tmp_path_outside):
        pmb.chroot.root(args, ["rm", "-r", tmp_path])
    pmb.chroot.user(args, ["mkdir", "-p", tmp_path])

    # No signature found
    pmb.chroot.user(args, ["tar", "-czf", tmp_path + "/no_sig.apk",
                           "/etc/issue"])
    with tarfile.open(tmp_path_outside + "/no_sig.apk", "r:gz") as tar:
        with pytest.raises(RuntimeError) as e:
            pmb.chroot.apk_static.read_signature_info(tar)
        assert "Could not find signature" in str(e.value)

    # Signature file with invalid name
    pmb.chroot.user(args, ["mkdir", "-p", tmp_path + "/sbin"])
    pmb.chroot.user(args, ["cp", "/etc/issue", tmp_path +
                           "/sbin/apk.static.SIGN.RSA.invalid.pub"])
    pmb.chroot.user(args, ["tar", "-czf", tmp_path + "/invalid_sig.apk",
                           "sbin/apk.static.SIGN.RSA.invalid.pub"],
                    working_dir=tmp_path)
    with tarfile.open(tmp_path_outside + "/invalid_sig.apk", "r:gz") as tar:
        with pytest.raises(RuntimeError) as e:
            pmb.chroot.apk_static.read_signature_info(tar)
        assert "Invalid signature key" in str(e.value)

    # Signature file with realistic name
    path = glob.glob(pmb.config.apk_keys_path + "/*.pub")[0]
    name = os.path.basename(path)
    path_archive = "sbin/apk.static.SIGN.RSA." + name
    pmb.chroot.user(args, ["mv", tmp_path + "/sbin/apk.static.SIGN.RSA.invalid.pub",
                           tmp_path + "/" + path_archive])
    pmb.chroot.user(args, ["tar", "-czf", tmp_path + "/realistic_name_sig.apk",
                           path_archive], working_dir=tmp_path)
    with tarfile.open(tmp_path_outside + "/realistic_name_sig.apk", "r:gz") as tar:
        sigfilename, sigkey_path = pmb.chroot.apk_static.read_signature_info(
            tar)
        assert sigfilename == path_archive
        assert sigkey_path == path

    # Clean up
    pmb.chroot.user(args, ["rm", "-r", tmp_path])


def test_successful_extraction(args, tmpdir):
    if os.path.exists(args.work + "/apk.static"):
        os.remove(args.work + "/apk.static")

    pmb.chroot.apk_static.init(args)
    assert os.path.exists(args.work + "/apk.static")
    os.remove(args.work + "/apk.static")


def test_signature_verification(args, tmpdir):
    if os.path.exists(args.work + "/apk.static"):
        os.remove(args.work + "/apk.static")

    version = pmb.parse.apkindex.package(args, "apk-tools-static")["version"]
    apk_path = pmb.chroot.apk_static.download(args,
                                              "apk-tools-static-" + version + ".apk")

    # Extract to temporary folder
    with tarfile.open(apk_path, "r:gz") as tar:
        sigfilename, sigkey_path = pmb.chroot.apk_static.read_signature_info(
            tar)
        files = pmb.chroot.apk_static.extract_temp(tar, sigfilename)

    # Verify signature (successful)
    pmb.chroot.apk_static.verify_signature(args, files, sigkey_path)

    # Append data to extracted apk.static
    with open(files["apk"]["temp_path"], "ab") as handle:
        handle.write("appended something".encode())

    # Verify signature again (fail) (this deletes the tempfiles)
    with pytest.raises(RuntimeError) as e:
        pmb.chroot.apk_static.verify_signature(args, files, sigkey_path)
    assert "Failed to validate signature" in str(e.value)

    #
    # Test "apk.static --version" check
    #
    with pytest.raises(RuntimeError) as e:
        pmb.chroot.apk_static.extract(args, "99.1.2-r1", apk_path)
    assert "downgrade attack" in str(e.value)


def test_outdated_version(args):
    if os.path.exists(args.work + "/apk.static"):
        os.remove(args.work + "/apk.static")

    # change min version
    min = pmb.config.apk_tools_static_min_version
    pmb.config.apk_tools_static_min_version = "99.1.2-r1"

    with pytest.raises(RuntimeError) as e:
        pmb.chroot.apk_static.init(args)
    assert "outdated version" in str(e.value)

    # reset min version
    pmb.config.apk_tools_static_min_version = min
