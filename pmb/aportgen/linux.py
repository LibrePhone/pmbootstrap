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
import pmb.helpers.run
import pmb.aportgen.core
import pmb.parse.apkindex
import pmb.parse.arch


def generate_apkbuild(args, pkgname, deviceinfo, patches):
    device = "-".join(pkgname.split("-")[1:])
    carch = pmb.parse.arch.alpine_to_kernel(deviceinfo["arch"])

    makedepends = "perl sed installkernel bash gmp-dev bc linux-headers elfutils-dev devicepkg-dev"

    package = """
            # kernel.release
            install -D "$builddir/include/config/kernel.release" \\
                "$pkgdir/usr/share/kernel/$_flavor/kernel.release"

            # zImage (find the right one)
            cd "$builddir/arch/$_carch/boot"
            _target="$pkgdir/boot/vmlinuz-$_flavor"
            for _zimg in zImage-dtb Image.gz-dtb *zImage Image; do
                [ -e "$_zimg" ] || continue
                msg "zImage found: $_zimg"
                install -Dm644 "$_zimg" "$_target"
                break
            done
            if ! [ -e "$_target" ]; then
                error "Could not find zImage in $PWD!"
                return 1
            fi"""

    build = """
            unset LDFLAGS
            make ARCH="$_carch" CC="${CC:-gcc}" \\
                KBUILD_BUILD_VERSION="$((pkgrel + 1 ))-postmarketOS\""""

    if deviceinfo["bootimg_qcdt"] == "true":
        makedepends += " dtbtool"

        build += """\n
            # Generate master DTB (deviceinfo_bootimg_qcdt)
            dtbTool -s 2048 -p "scripts/dtc/" -o "arch/""" + carch + "/boot/dt.img\" \"arch/" + carch + "/boot/\""

        package += """\n
            # Master DTB (deviceinfo_bootimg_qcdt)
            install -Dm644 "$builddir/arch/""" + carch + """/boot/dt.img" \\
                "$pkgdir/boot/dt.img\""""

    content = """\
        # Reference: <https://postmarketos.org/vendorkernel>
        # Kernel config based on: arch/""" + carch + """/configs/(CHANGEME!)

        pkgname=\"""" + pkgname + """\"
        pkgver=3.x.x
        pkgrel=0
        pkgdesc=\"""" + deviceinfo["name"] + """ kernel fork\"
        arch=\"""" + deviceinfo["arch"] + """\"
        _carch=\"""" + carch + """\"
        _flavor=\"""" + device + """\"
        url="https://kernel.org"
        license="GPL-2.0-only"
        options="!strip !check !tracedeps"
        makedepends=\"""" + makedepends + """\"

        # Compiler: latest GCC from Alpine
        HOSTCC="${CC:-gcc}"
        HOSTCC="${HOSTCC#${CROSS_COMPILE}}"

        # Source
        _repository="(CHANGEME!)"
        _commit="ffffffffffffffffffffffffffffffffffffffff"
        _config="config-${_flavor}.${arch}"
        source="
            $pkgname-$_commit.tar.gz::https://github.com/LineageOS/${_repository}/archive/${_commit}.tar.gz
            $_config""" + ("\n" + " " * 12).join([""] + patches) + """
        "
        builddir="$srcdir/${_repository}-${_commit}"

        prepare() {
            default_prepare
            downstreamkernel_prepare "$srcdir" "$builddir" "$_config" "$_carch" "$HOSTCC"
        }

        build() {""" + build + """
        }

        package() {""" + package + """
        }

        sha512sums="(run 'pmbootstrap checksum """ + pkgname + """' to fill)\""""

    # Write the file
    with open(args.work + "/aportgen/APKBUILD", "w", encoding="utf-8") as handle:
        for line in content.split("\n"):
            handle.write(line[8:].replace(" " * 4, "\t") + "\n")


def generate(args, pkgname):
    device = "-".join(pkgname.split("-")[1:])
    deviceinfo = pmb.parse.deviceinfo(args, device)

    # Symlink commonly used patches
    pmb.helpers.run.user(args, ["mkdir", "-p", args.work + "/aportgen"])
    patches = [
        "gcc7-give-up-on-ilog2-const-optimizations.patch",
        "gcc8-fix-put-user.patch",
        "kernel-use-the-gnu89-standard-explicitly.patch",
    ]
    for patch in patches:
        pmb.helpers.run.user(args, ["ln", "-s",
                                    "../../.shared-patches/linux/" + patch,
                                    args.work + "/aportgen/" + patch])

    generate_apkbuild(args, pkgname, deviceinfo, patches)
