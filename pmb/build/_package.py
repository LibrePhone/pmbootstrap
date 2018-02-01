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
import os
import logging

import pmb.build
import pmb.build.autodetect
import pmb.chroot
import pmb.chroot.apk
import pmb.chroot.distccd
import pmb.helpers.repo
import pmb.parse
import pmb.parse.arch


def skip_already_built(args, pkgname, arch):
    """
    Check if the package was already built in this session, and add it
    to the cache in case it was not built yet.

    :returns: True when it can be skipped or False
    """
    if arch not in args.cache["built"]:
        args.cache["built"][arch] = []
    if pkgname in args.cache["built"][arch]:
        logging.verbose(pkgname + ": already checked this session,"
                        " no need to build it or its dependencies")
        return True
    args.cache["built"][arch].append(pkgname)
    return False


def get_apkbuild(args, pkgname, arch):
    """
    Find the APKBUILD path for pkgname. When there is none, try to find it in
    the binary package APKINDEX files or raise an exception.

    :param pkgname: package name to be built, as specified in the APKBUILD
    :returns: None or full path to APKBUILD
    """
    # Get existing binary package indexes
    pmb.helpers.repo.update(args)

    # Get aport, skip upstream only packages
    aport = pmb.build.find_aport(args, pkgname, False)
    if aport:
        return pmb.parse.apkbuild(args, aport + "/APKBUILD")
    if pmb.parse.apkindex.read_any_index(args, pkgname, arch):
        return None
    raise RuntimeError("Package '" + pkgname + "': Could not find aport, and"
                       " could not find this package in any APKINDEX!")


def check_arch(args, apkbuild, arch):
    """
    Check if the APKBUILD can be built for a specific architecture and abort
    with a helpful message if it is not the case.
    """
    for value in [arch, "all", "noarch"]:
        if value in apkbuild["arch"]:
            return

    pkgname = apkbuild["pkgname"]
    logging.info("NOTE: You can edit the 'arch=' line inside the APKBUILD")
    if args.action == "build":
        logging.info("NOTE: Alternatively, use --arch to build for another"
                     " architecture ('pmbootstrap build --arch=armhf " +
                     pkgname + "')")
    raise RuntimeError("Can't build '" + pkgname + "' for architecture " +
                       arch)


def get_depends(args, apkbuild):
    """
    Alpine's abuild always builds/installs the "depends" and "makedepends"
    of a package before building it. We used to only care about "makedepends"
    and it's still possible to ignore the depends with --ignore-depends.

    :returns: list of dependency pkgnames (eg. ["sdl2", "sdl2_net"])
    """
    # Read makedepends and depends
    ret = list(apkbuild["makedepends"])
    if "ignore_depends" not in args or not args.ignore_depends:
        ret += apkbuild["depends"]
    ret = sorted(set(ret))

    # Don't recurse forever when a package depends on itself (#948)
    for pkgname in [apkbuild["pkgname"]] + list(apkbuild["subpackages"]):
        if pkgname in ret:
            logging.verbose(apkbuild["pkgname"] + ": ignoring dependency on"
                            " itself: " + pkgname)
            ret.remove(pkgname)
    return ret


def build_depends(args, apkbuild, arch, strict):
    """
    Get and build dependencies with verbose logging messages.

    :returns: (depends, depends_built)
    """
    # Get dependencies
    pkgname = apkbuild["pkgname"]
    depends = get_depends(args, apkbuild)
    logging.verbose(pkgname + ": build/install dependencies: " +
                    ", ".join(depends))

    # Build them
    depends_built = []
    for depend in depends:
        if package(args, depend, arch, strict=strict):
            depends_built += [depend]
    logging.verbose(pkgname + ": build dependencies: done, built: " +
                    ", ".join(depends_built))

    return (depends, depends_built)


def is_necessary_warn_depends(args, apkbuild, arch, force, depends_built):
    """
    Check if a build is necessary, and warn if it is not, but there were
    dependencies built.

    :returns: True or False
    """
    pkgname = apkbuild["pkgname"]
    ret = True if force else pmb.build.is_necessary(args, arch, apkbuild)

    if not ret and len(depends_built):
        # Warn of potentially outdated package
        logging.warning("WARNING: " + pkgname + " depends on rebuilt" +
                        " package(s) " + ",".join(depends_built) + " (use" +
                        " 'pmbootstrap build " + pkgname + " --force' if" +
                        " necessary!)")

    logging.verbose(pkgname + ": build necessary: " + str(ret))
    return ret


def init_buildenv(args, apkbuild, arch, strict=False, force=False, cross=None,
                  suffix="native", skip_init_buildenv=False):
    """
    Build all dependencies, check if we need to build at all (otherwise we've
    just initialized the build environment for nothing) and then setup the
    whole build environment (abuild, gcc, dependencies, cross-compiler).

    :param cross: None, "native" or "distcc"
    :param skip_init_buildenv: can be set to False to avoid initializing the
                               build environment. Use this when building
                               something during initialization of the build
                               environment (e.g. qemu aarch64 bug workaround)
    :returns: True when the build is necessary (otherwise False)
    """
    # Build dependencies (package arch)
    depends, built = build_depends(args, apkbuild, arch, strict)

    # Check if build is necessary
    if not is_necessary_warn_depends(args, apkbuild, arch, force, built):
        return False

    # Install and configure abuild, ccache, gcc, dependencies
    if not skip_init_buildenv:
        pmb.build.init(args, suffix)
        pmb.build.other.configure_abuild(args, suffix)
        pmb.build.other.configure_ccache(args, suffix)
    if not strict and len(depends):
        pmb.chroot.apk.install(args, depends, suffix)

    # Cross-compiler init
    if cross:
        pmb.chroot.apk.install(args, ["gcc-" + arch, "g++-" + arch,
                                      "ccache-cross-symlinks"])
    if cross == "distcc":
        pmb.chroot.apk.install(args, ["distcc", "arch-bin-masquerade"],
                               suffix=suffix)
        pmb.chroot.distccd.start(args, arch)

    # "native" cross-compile: build and install dependencies (#1061)
    if cross == "native":
        depends, built = build_depends(args, apkbuild, args.arch_native, strict)
        if not strict and len(depends):
            pmb.chroot.apk.install(args, depends)

    return True


def get_gcc_version(args, arch):
    """
    Get the GCC version for a specific arch from parsing the right APKINDEX.
    We feed this to ccache, so it knows the right GCC version, when
    cross-compiling in a foreign arch chroot with distcc. See the "using
    ccache with other compiler wrappers" section of their man page:
    <https://linux.die.net/man/1/ccache>
    :returns: a string like "6.4.0-r5"
    """
    repository = args.mirror_alpine + args.alpine_version + "/main"
    hash = pmb.helpers.repo.hash(repository)
    index_path = (args.work + "/cache_apk_" + arch + "/APKINDEX." +
                  hash + ".tar.gz")
    apkindex = pmb.parse.apkindex.read(args, "gcc", index_path, True)
    return apkindex["version"]


def run_abuild(args, apkbuild, arch, strict=False, force=False, cross=None,
               suffix="native"):
    """
    Set up all environment variables and construct the abuild command (all
    depending on the cross-compiler method and target architecture), copy
    the aport to the chroot and execute abuild.

    :param cross: None, "native" or "distcc"
    :returns: (output, cmd, env), output is the destination apk path relative
              to the package folder ("x86_64/hello-1-r2.apk"). cmd and env are
              used by the test case, and they are the full abuild command and
              the environment variables dict generated in this function.
    """
    # Sanity check
    if cross == "native" and "!tracedeps" not in apkbuild["options"]:
        logging.info("WARNING: Option !tracedeps is not set, but we're"
                     " cross-compiling in the native chroot. This will"
                     " probably fail!")

    # Pretty log message
    output = (arch + "/" + apkbuild["pkgname"] + "-" + apkbuild["pkgver"] +
              "-r" + apkbuild["pkgrel"] + ".apk")
    logging.info("(" + suffix + ") build " + output)

    # Environment variables
    env = {"CARCH": arch}
    if cross == "native":
        hostspec = pmb.parse.arch.alpine_to_hostspec(arch)
        env["CROSS_COMPILE"] = hostspec + "-"
        env["CC"] = hostspec + "-gcc"
    if cross == "distcc":
        env["CCACHE_PREFIX"] = "distcc"
        env["CCACHE_PATH"] = "/usr/lib/arch-bin-masquerade/" + arch + ":/usr/bin"
        env["CCACHE_COMPILERCHECK"] = "string:" + get_gcc_version(args, arch)
        env["DISTCC_HOSTS"] = "127.0.0.1:" + args.port_distccd

    # Build the abuild command
    cmd = []
    for key, value in env.items():
        cmd += [key + "=" + value]
    cmd += ["abuild"]
    if strict:
        cmd += ["-r"]  # install depends with abuild
    else:
        cmd += ["-d"]  # do not install depends with abuild
    if force:
        cmd += ["-f"]

    # Copy the aport to the chroot and build it
    pmb.build.copy_to_buildpath(args, apkbuild["pkgname"], suffix)
    pmb.chroot.user(args, cmd, suffix, "/home/pmos/build")
    return (output, cmd, env)


def finish(args, apkbuild, arch, output, strict=False, suffix="native"):
    """
    Various finishing tasks that need to be done after a build.
    """
    # Verify output file
    path = args.work + "/packages/" + output
    if not os.path.exists(path):
        raise RuntimeError("Package not found after build: " + path)

    # Clear APKINDEX cache (we only parse APKINDEX files once per session and
    # cache the result for faster dependency resolving, but after we built a
    # package we need to parse it again)
    pmb.parse.apkindex.clear_cache(args, args.work + "/packages/" +
                                   arch + "/APKINDEX.tar.gz")

    # Uninstall build dependencies (strict mode)
    if strict:
        logging.info("(" + suffix + ") uninstall build dependencies")
        pmb.chroot.user(args, ["abuild", "undeps"], suffix, "/home/pmos/build")


def package(args, pkgname, arch=None, force=False, strict=False,
            skip_init_buildenv=False):
    """
    Build a package and its dependencies with Alpine Linux' abuild.

    :param pkgname: package name to be built, as specified in the APKBUILD
    :param arch: architecture we're building for (default: native)
    :param force: even build, if not necessary
    :param strict: avoid building with irrelevant dependencies installed by
                   letting abuild install and uninstall all dependencies.
    :param skip_init_buildenv: can be set to False to avoid initializing the
                               build environment. Use this when building
                               something during initialization of the build
                               environment (e.g. qemu aarch64 bug workaround)
    :returns: None if the build was not necessary
              output path relative to the packages folder ("armhf/ab-1-r2.apk")
    """
    # Once per session is enough
    arch = arch or args.arch_native
    if skip_already_built(args, pkgname, arch):
        return

    # Only build when APKBUILD exists
    apkbuild = get_apkbuild(args, pkgname, arch)
    if not apkbuild:
        return

    # Detect the build environment (skip unnecessary builds)
    check_arch(args, apkbuild, arch)
    suffix = pmb.build.autodetect.suffix(args, apkbuild, arch)
    cross = pmb.build.autodetect.crosscompile(args, apkbuild, arch, suffix)
    if not init_buildenv(args, apkbuild, arch, strict, force, cross, suffix,
                         skip_init_buildenv):
        return

    # Build and finish up
    (output, cmd, env) = run_abuild(args, apkbuild, arch, strict, force, cross,
                                    suffix)
    finish(args, apkbuild, arch, output, strict, suffix)
    return output
