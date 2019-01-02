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
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, pmb_src)
import pmb.chroot.apk_static
import pmb.parse.apkindex
import pmb.helpers.logging
import pmb.parse.bootimg


@pytest.fixture
def args(request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_bootimg_invalid_path(args):
    with pytest.raises(RuntimeError) as e:
        pmb.parse.bootimg(args, "/invalid-path")
    assert "Could not find file" in str(e.value)


def test_bootimg_kernel(args):
    path = pmb_src + "/test/testdata/bootimg/kernel-boot.img"
    with pytest.raises(RuntimeError) as e:
        pmb.parse.bootimg(args, path)
    assert "heimdall-isorec" in str(e.value)


def test_bootimg_invalid_file(args):
    with pytest.raises(RuntimeError) as e:
        pmb.parse.bootimg(args, __file__)
    assert "File is not an Android boot.img" in str(e.value)


def test_bootimg_normal(args):
    path = pmb_src + "/test/testdata/bootimg/normal-boot.img"
    output = {"base": "0x80000000",
              "kernel_offset": "0x00008000",
              "ramdisk_offset": "0x04000000",
              "second_offset": "0x00f00000",
              "tags_offset": "0x0e000000",
              "pagesize": "2048",
              "cmdline": "bootopt=64S3,32S1,32S1",
              "qcdt": "false"}
    assert pmb.parse.bootimg(args, path) == output


def test_bootimg_qcdt(args):
    path = pmb_src + "/test/testdata/bootimg/qcdt-boot.img"
    output = {"base": "0x80000000",
              "kernel_offset": "0x00008000",
              "ramdisk_offset": "0x04000000",
              "second_offset": "0x00f00000",
              "tags_offset": "0x0e000000",
              "pagesize": "2048",
              "cmdline": "bootopt=64S3,32S1,32S1",
              "qcdt": "true"}
    assert pmb.parse.bootimg(args, path) == output
