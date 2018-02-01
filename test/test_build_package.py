"""
Copyright 2018 Oliver Smith

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

"""
This file tests all functions from pmb.build._package.
"""

import os
import pytest
import sys

# Import from parent directory
sys.path.append(os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.build
import pmb.build._package
import pmb.config
import pmb.config.init
import pmb.helpers.logging


@pytest.fixture
def args(tmpdir, request):
    import pmb.parse
    sys.argv = ["pmbootstrap", "init"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def return_none(*args, **kwargs):
    return None


def return_string(*args, **kwargs):
    return "some/random/path.apk"


def return_true(*args, **kwargs):
    return True


def return_false(*args, **kwargs):
    return False


def return_fake_build_depends(*args, **kwargs):
    """
    Fake return value for pmb.build._package.build_depends:
    depends: ["alpine-base"], depends_built: []
    """
    return (["alpine-base"], [])


def args_patched(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", argv)
    return pmb.parse.arguments()


def test_skip_already_built(args):
    func = pmb.build._package.skip_already_built
    assert args.cache["built"] == {}
    assert func(args, "test-package", "armhf") is False
    assert args.cache["built"] == {"armhf": ["test-package"]}
    assert func(args, "test-package", "armhf") is True


def test_get_apkbuild(args):
    func = pmb.build._package.get_apkbuild

    # Valid aport
    pkgname = "postmarketos-base"
    assert func(args, pkgname, "x86_64")["pkgname"] == pkgname

    # Valid binary package
    assert func(args, "alpine-base", "x86_64") is None

    # Invalid package
    with pytest.raises(RuntimeError) as e:
        func(args, "invalid-package-name", "x86_64")
    assert "Could not find" in str(e.value)


def test_check_arch(args):
    func = pmb.build._package.check_arch
    apkbuild = {"pkgname": "test"}

    # Arch is right
    apkbuild["arch"] = ["armhf"]
    func(args, apkbuild, "armhf")
    apkbuild["arch"] = ["noarch"]
    func(args, apkbuild, "armhf")
    apkbuild["arch"] = ["all"]
    func(args, apkbuild, "armhf")

    # Arch is wrong
    apkbuild["arch"] = ["x86_64"]
    with pytest.raises(RuntimeError) as e:
        func(args, apkbuild, "armhf")
    assert "Can't build" in str(e.value)


def test_get_depends(monkeypatch):
    func = pmb.build._package.get_depends
    apkbuild = {"pkgname": "test", "depends": ["a"], "makedepends": ["c", "b"],
                "subpackages": ["d"]}

    # Depends + makedepends
    args = args_patched(monkeypatch, ["pmbootstrap", "build", "test"])
    assert func(args, apkbuild) == ["a", "b", "c"]
    args = args_patched(monkeypatch, ["pmbootstrap", "install"])
    assert func(args, apkbuild) == ["a", "b", "c"]

    # Ignore depends (-i)
    args = args_patched(monkeypatch, ["pmbootstrap", "build", "-i", "test"])
    assert func(args, apkbuild) == ["b", "c"]

    # Package depends on its own subpackage
    apkbuild["makedepends"] = ["d"]
    args = args_patched(monkeypatch, ["pmbootstrap", "build", "test"])
    assert func(args, apkbuild) == ["a"]

    # Package depends on itself
    apkbuild["makedepends"] = ["c", "b", "test"]
    args = args_patched(monkeypatch, ["pmbootstrap", "build", "test"])
    assert func(args, apkbuild) == ["a", "b", "c"]


def test_build_depends(args, monkeypatch):
    # Shortcut and fake apkbuild
    func = pmb.build._package.build_depends
    apkbuild = {"pkgname": "test", "depends": ["a"], "makedepends": ["b"],
                "subpackages": ["d"]}

    # No depends built (first makedepends + depends, then only makedepends)
    monkeypatch.setattr(pmb.build._package, "package", return_none)
    assert func(args, apkbuild, "armhf", True) == (["a", "b"], [])

    # All depends built (makedepends only)
    monkeypatch.setattr(pmb.build._package, "package", return_string)
    assert func(args, apkbuild, "armhf", False) == (["a", "b"], ["a", "b"])


def test_is_necessary_warn_depends(args, monkeypatch):
    # Shortcut and fake apkbuild
    func = pmb.build._package.is_necessary_warn_depends
    apkbuild = {"pkgname": "test"}

    # Necessary
    monkeypatch.setattr(pmb.build, "is_necessary", return_true)
    assert func(args, apkbuild, "armhf", False, []) is True

    # Necessary (strict=True overrides is_necessary())
    monkeypatch.setattr(pmb.build, "is_necessary", return_false)
    assert func(args, apkbuild, "armhf", True, []) is True

    # Not necessary (with depends: different code path that prints a warning)
    assert func(args, apkbuild, "armhf", False, []) is False
    assert func(args, apkbuild, "armhf", False, ["first", "second"]) is False


def test_init_buildenv(args, monkeypatch):
    # Disable effects of functions we don't want to test here
    monkeypatch.setattr(pmb.build._package, "build_depends",
                        return_fake_build_depends)
    monkeypatch.setattr(pmb.build._package, "is_necessary_warn_depends",
                        return_true)
    monkeypatch.setattr(pmb.chroot.apk, "install", return_none)
    monkeypatch.setattr(pmb.chroot.distccd, "start", return_none)

    # Shortcut and fake apkbuild
    func = pmb.build._package.init_buildenv
    apkbuild = {"pkgname": "test", "depends": ["a"], "makedepends": ["b"]}

    # Build is necessary (various code paths)
    assert func(args, apkbuild, "armhf", strict=True) is True
    assert func(args, apkbuild, "armhf", cross="native") is True
    assert func(args, apkbuild, "armhf", cross="distcc") is True

    # Build is not necessary (only builds dependencies)
    monkeypatch.setattr(pmb.build._package, "is_necessary_warn_depends",
                        return_false)
    assert func(args, apkbuild, "armhf") is False


def test_run_abuild(args, monkeypatch):
    # Disable effects of functions we don't want to test here
    monkeypatch.setattr(pmb.build, "copy_to_buildpath", return_none)
    monkeypatch.setattr(pmb.chroot, "user", return_none)

    # Shortcut and fake apkbuild
    func = pmb.build._package.run_abuild
    apkbuild = {"pkgname": "test", "pkgver": "1", "pkgrel": "2", "options": []}

    # Normal run
    output = "armhf/test-1-r2.apk"
    env = {"CARCH": "armhf"}
    cmd = ["CARCH=armhf", "abuild", "-d"]
    assert func(args, apkbuild, "armhf") == (output, cmd, env)

    # Force and strict
    cmd = ["CARCH=armhf", "abuild", "-r", "-f"]
    assert func(args, apkbuild, "armhf", True, True) == (output, cmd, env)

    # cross=native
    env = {"CARCH": "armhf",
           "CROSS_COMPILE": "armv6-alpine-linux-muslgnueabihf-",
           "CC": "armv6-alpine-linux-muslgnueabihf-gcc"}
    cmd = ["CARCH=armhf", "CROSS_COMPILE=armv6-alpine-linux-muslgnueabihf-",
           "CC=armv6-alpine-linux-muslgnueabihf-gcc", "abuild", "-d"]
    assert func(args, apkbuild, "armhf", cross="native") == (output, cmd, env)

    # cross=distcc
    (output, cmd, env) = func(args, apkbuild, "armhf", cross="distcc")
    assert output == "armhf/test-1-r2.apk"
    assert env["CARCH"] == "armhf"
    assert env["CCACHE_PREFIX"] == "distcc"
    assert env["CCACHE_PATH"] == "/usr/lib/arch-bin-masquerade/armhf:/usr/bin"
    assert env["CCACHE_COMPILERCHECK"].startswith("string:")
    assert env["DISTCC_HOSTS"] == "127.0.0.1:33632"


def test_finish(args, monkeypatch):
    # Real output path
    output = pmb.build.package(args, "hello-world", force=True)

    # Disable effects of functions we don't want to test below
    monkeypatch.setattr(pmb.chroot, "user", return_none)

    # Shortcut and fake apkbuild
    func = pmb.build._package.finish
    apkbuild = {}

    # Non-existing output path
    with pytest.raises(RuntimeError) as e:
        func(args, apkbuild, "armhf", "/invalid/path")
    assert "Package not found" in str(e.value)

    # Existing output path
    func(args, apkbuild, args.arch_native, output)


def test_package(args):
    # First build
    assert pmb.build.package(args, "hello-world", force=True)

    # Package exists
    args.cache["built"] = {}
    assert pmb.build.package(args, "hello-world") is None

    # Force building again
    args.cache["built"] = {}
    assert pmb.build.package(args, "hello-world", force=True)

    # Build for another architecture
    assert pmb.build.package(args, "hello-world", "armhf", force=True)

    # Upstream package, for which we don't have an aport
    assert pmb.build.package(args, "alpine-base") is None


def test_build_depends_high_level(args, monkeypatch):
    """
    "hello-world-wrapper" depends on "hello-world". We build both, then delete
    "hello-world" and check that it gets rebuilt correctly again.
    """
    # Patch pmb.build.is_necessary() to always build the hello-world package
    def fake_build_is_necessary(args, arch, apkbuild, apkindex_path=None):
        if apkbuild["pkgname"] == "hello-world":
            return True
        return pmb.build.other.is_necessary(args, arch, apkbuild,
                                            apkindex_path)
    monkeypatch.setattr(pmb.build, "is_necessary",
                        fake_build_is_necessary)

    # Build hello-world to get its full output path
    output_hello = pmb.build.package(args, "hello-world")
    output_hello_outside = args.work + "/packages/" + output_hello
    assert os.path.exists(output_hello_outside)

    # Make sure the wrapper exists
    pmb.build.package(args, "hello-world-wrapper")

    # Remove hello-world
    pmb.helpers.run.root(args, ["rm", output_hello_outside])
    pmb.build.index_repo(args, args.arch_native)
    args.cache["built"] = {}

    # Ask to build the wrapper. It should not build the wrapper (it exists, not
    # using force), but build/update its missing dependency "hello-world"
    # instead.
    assert pmb.build.package(args, "hello-world-wrapper") is None
    assert os.path.exists(output_hello_outside)
