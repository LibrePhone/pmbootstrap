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
#!/usr/bin/env python3
import os
import sys
import tarfile
import glob
import pytest

# Import from parent directory
pmb_src = os.path.abspath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.append(pmb_src)
import pmb.chroot.apk_static
import pmb.parse.apkindex


@pytest.fixture
def args():
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    setattr(args, "logfd", open("/dev/null", "a+"))
    yield args
    args.logfd.close()


def test_read_signature_info(tmpdir):
    with tarfile.open(tmpdir + "/test.apk", "w:gz") as tar:
        # No signature found
        with pytest.raises(RuntimeError) as e:
            pmb.chroot.apk_static.read_signature_info(tar)
        assert "Could not find signature" in str(e.value)

        # Add signature file with invalid name
        tar.add(__file__, "sbin/apk.static.SIGN.RSA.invalid.pub")
        with pytest.raises(RuntimeError) as e:
            pmb.chroot.apk_static.read_signature_info(tar)
        assert "Invalid signature key" in str(e.value)

    # Add signature file with realistic name
    path = glob.glob(pmb_src + "/keys/*.pub")[0]
    name = os.path.basename(path)
    path_archive = "sbin/apk.static.SIGN.RSA." + name
    with tarfile.open(tmpdir + "/test2.apk", "w:gz") as tar:
        tar.add(__file__, path_archive)
        sigfilename, sigkey_path = pmb.chroot.apk_static.read_signature_info(
            tar)
    assert sigfilename == path_archive
    assert sigkey_path == path


def test_successful_extraction(args, tmpdir):
    if os.path.exists(args.work + "/apk.static"):
        os.remove(args.work + "/apk.static")

    pmb.chroot.apk_static.init(args)
    assert os.path.exists(args.work + "/apk.static")
    os.remove(args.work + "/apk.static")


def test_signature_verification(args, tmpdir):
    if os.path.exists(args.work + "/apk.static"):
        os.remove(args.work + "/apk.static")

    apk_index = pmb.chroot.apk_static.download(args, "APKINDEX.tar.gz")
    version = pmb.parse.apkindex.read(args, "apk-tools-static",
                                      apk_index)["version"]
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
