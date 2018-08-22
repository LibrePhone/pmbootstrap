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

import pmb.aportgen
import pmb.aportgen.core
import pmb.build
import pmb.build.envkernel
import pmb.config
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


def test_package_kernel_args(args):
    args.packages = ["package-one", "package-two"]
    with pytest.raises(RuntimeError) as e:
        pmb.build.envkernel.package_kernel(args)
    assert "--envkernel needs exactly one linux-* package as argument." in \
        str(e.value)


def test_find_kbuild_output_dir(args):
    # Test parsing an APKBUILD
    pkgname = "linux-envkernel-test"
    testdata = pmb_src + "/test/testdata"
    path = testdata + "/apkbuild/APKBUILD." + pkgname
    function_body = pmb.parse.function_body(path, "package")
    kbuild_out = pmb.build.envkernel.find_kbuild_output_dir(args,
                                                            function_body)
    assert kbuild_out == "build"

    # Test full function body
    function_body = [
        "   install -Dm644 \"$srcdir\"/build/arch/arm/boot/dt.img ",
        "       \"$pkgdir\"/boot/dt.img",
        "",
        "   install -Dm644 \"$srcdir\"/build/arch/arm/boot/zImage-dtb ",
        "       \"$pkgdir\"/boot/vmlinuz-$_flavor",
        "",
        "   install -D \"$srcdir\"/build/include/config/kernel.release ",
        "       \"$pkgdir\"/usr/share/kernel/$_flavor/kernel.release",
        "",
        "   cd \"$srcdir\"/build",
        "   unset LDFLAGS",
        "",
        "   make ARCH=\"$_carch\" CC=\"${CC:-gcc}\" ",
        "       KBUILD_BUILD_VERSION=\"$((pkgrel + 1))-Alpine\" ",
        "       INSTALL_MOD_PATH=\"$pkgdir\" modules_install",
    ]
    kbuild_out = pmb.build.envkernel.find_kbuild_output_dir(args,
                                                            function_body)
    assert kbuild_out == "build"

    # Test no kbuild out dir
    function_body = [
        "   install -Dm644 \"$srcdir\"/arch/arm/boot/zImage ",
        "       \"$pkgdir\"/boot/vmlinuz-$_flavor",
        "   install -D \"$srcdir\"/include/config/kernel.release ",
        "       \"$pkgdir\"/usr/share/kernel/$_flavor/kernel.release",
    ]
    kbuild_out = pmb.build.envkernel.find_kbuild_output_dir(args,
                                                            function_body)
    assert kbuild_out == ""

    # Test curly brackets around srcdir
    function_body = [
        "   install -Dm644 \"${srcdir}\"/build/arch/arm/boot/zImage ",
        "       \"$pkgdir\"/boot/vmlinuz-$_flavor",
        "   install -D \"${srcdir}\"/build/include/config/kernel.release ",
        "       \"$pkgdir\"/usr/share/kernel/$_flavor/kernel.release",
    ]
    kbuild_out = pmb.build.envkernel.find_kbuild_output_dir(args,
                                                            function_body)
    assert kbuild_out == "build"

    # Test multiple sub directories
    function_body = [
        "   install -Dm644 \"${srcdir}\"/sub/dir/arch/arm/boot/zImage-dtb ",
        "       \"$pkgdir\"/boot/vmlinuz-$_flavor",
        "   install -D \"${srcdir}\"/sub/dir/include/config/kernel.release ",
        "       \"$pkgdir\"/usr/share/kernel/$_flavor/kernel.release",
    ]
    kbuild_out = pmb.build.envkernel.find_kbuild_output_dir(args,
                                                            function_body)
    assert kbuild_out == "sub/dir"

    # Test no kbuild out dir found
    function_body = [
        "   install -Dm644 \"$srcdir\"/build/not/found/zImage-dtb ",
        "       \"$pkgdir\"/boot/vmlinuz-$_flavor",
        "   install -D \"$srcdir\"/not/found/kernel.release ",
        "       \"$pkgdir\"/usr/share/kernel/$_flavor/kernel.release",
    ]
    with pytest.raises(RuntimeError) as e:
        kbuild_out = pmb.build.envkernel.find_kbuild_output_dir(args,
                                                                function_body)
    assert ("Couldn't find a kbuild out directory. Is your APKBUILD messed up?"
            " If not, then consider adjusting the patterns in "
            "pmb/build/envkernel.py to work with your APKBUILD, or submit an "
            "issue.") in str(e.value)

    # Test multiple different kbuild out dirs
    function_body = [
        "   install -Dm644 \"$srcdir\"/build/arch/arm/boot/zImage-dtb ",
        "       \"$pkgdir\"/boot/vmlinuz-$_flavor",
        "   install -D \"$srcdir\"/include/config/kernel.release ",
        "       \"$pkgdir\"/usr/share/kernel/$_flavor/kernel.release",
    ]
    with pytest.raises(RuntimeError) as e:
        kbuild_out = pmb.build.envkernel.find_kbuild_output_dir(args,
                                                                function_body)
    assert ("Multiple kbuild out directories found. Can you modify your "
            "APKBUILD so it only has one output path? If you can't resolve it,"
            " please open an issue.") in str(e.value)
