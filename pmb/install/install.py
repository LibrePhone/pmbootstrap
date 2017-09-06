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
import logging
import os
import glob

import pmb.chroot
import pmb.chroot.apk
import pmb.chroot.other
import pmb.chroot.initfs
import pmb.config
import pmb.helpers.run
import pmb.install.blockdevice
import pmb.install.file
import pmb.install.recovery
import pmb.install


def mount_device_rootfs(args, suffix="native"):
    """
    Mount the device rootfs.
    """
    mountpoint = "/mnt/rootfs_" + args.device
    pmb.helpers.mount.bind(args, args.work + "/chroot_rootfs_" + args.device,
                           args.work + "/chroot_" + suffix + mountpoint)
    return mountpoint


def get_subpartitions_size(args):
    """
    Calculate the size of the whole image and boot subpartition.

    :returns: (full, boot) the size of the full image and boot
              partition as integer in bytes
    """
    # Calculate required sizes first
    chroot = args.work + "/chroot_rootfs_" + args.device
    root = pmb.helpers.other.folder_size(args, chroot)
    boot = pmb.helpers.other.folder_size(args, chroot + "/boot")
    home = pmb.helpers.other.folder_size(args, chroot + "/home")

    # The home folder gets omitted when copying the rootfs to
    # /dev/installp2
    full = root - home

    # Add some free space, see also:
    # https://github.com/postmarketOS/pmbootstrap/pull/336
    full *= 1.20
    boot += 15 * 1024 * 1024
    return (full, boot)


def copy_files_from_chroot(args):
    """
    Copy all files from the rootfs chroot to /mnt/install, except
    for the home folder (because /home will contain some empty
    mountpoint folders).
    """
    # Mount the device rootfs
    logging.info("(native) copy rootfs_" + args.device + " to" +
                 " /mnt/install/")
    mountpoint = mount_device_rootfs(args)
    mountpoint_outside = args.work + "/chroot_native" + mountpoint

    # Get all folders inside the device rootfs (except for home)
    folders = []
    for path in glob.glob(mountpoint_outside + "/*"):
        if path.endswith("/home"):
            continue
        folders += [os.path.basename(path)]

    # Run the copy command
    pmb.chroot.root(args, ["cp", "-a"] + folders + ["/mnt/install/"],
                    working_dir=mountpoint)


def copy_files_other(args):
    """
    Copy over keys, create /home/user.
    """
    # Copy over keys
    rootfs = args.work + "/chroot_native/mnt/install"
    for key in glob.glob(args.work + "/config_apk_keys/*.pub"):
        pmb.helpers.run.root(args, ["cp", key, rootfs + "/etc/apk/keys/"])

    # Create /home/user
    pmb.helpers.run.root(args, ["mkdir", "-p", rootfs + "/home/user"])
    pmb.helpers.run.root(args, ["chown", pmb.config.chroot_uid_user,
                                rootfs + "/home/user"])


def set_user_password(args):
    """
    Loop until the passwords for user and root have been changed successfully.
    """
    logging.info(" *** SET LOGIN PASSWORD FOR: 'user' ***")
    suffix = "rootfs_" + args.device
    while True:
        try:
            pmb.chroot.root(args, ["passwd", "user"], suffix, log=False)
            break
        except RuntimeError:
            logging.info("WARNING: Failed to set the password. Try it"
                         " one more time.")
            pass


def copy_ssh_key(args):
    """
    Offer to copy user's SSH public key to the device if it exists
    """
    user_ssh_pubkey = os.path.expanduser("~/.ssh/id_rsa.pub")
    target = args.work + "/chroot_native/mnt/install/home/user/.ssh"
    if os.path.exists(user_ssh_pubkey):
        if pmb.helpers.cli.confirm(args, "Would you like to copy your SSH public key to the device?"):
            pmb.helpers.run.root(args, ["mkdir", target])
            pmb.helpers.run.root(args, ["chmod", "700", target])
            pmb.helpers.run.root(args, ["cp", user_ssh_pubkey, target + "/authorized_keys"])
            pmb.helpers.run.root(args, ["chown", "-R", "12345:12345", target])
    else:
        logging.info("NOTE: No public SSH key found, you will only be able to use SSH password authentication!")


def setup_keymap(args):
    """
    Set the keymap with the setup-keymap utility if the device requires it
    """
    suffix = "rootfs_" + args.device
    info = pmb.parse.deviceinfo(args, device=args.device)
    if "keymaps" not in info or info["keymaps"].strip() == "":
        logging.info("NOTE: No valid keymap specified for device")
        return
    options = info["keymaps"].split(' ')
    if (args.keymap != "" and
            args.keymap is not None and
            args.keymap in options):
        layout, variant = args.keymap.split("/")
        pmb.chroot.root(args, ["setup-keymap", layout, variant], suffix, log=False)
    else:
        logging.info("NOTE: No valid keymap specified for device")


def install_system_image(args):
    # Partition and fill image/sdcard
    logging.info("*** (3/5) PREPARE INSTALL BLOCKDEVICE ***")
    pmb.chroot.shutdown(args, True)
    (size_image, size_boot) = get_subpartitions_size(args)
    pmb.install.blockdevice.create(args, size_image)
    pmb.install.partition(args, size_boot)
    pmb.install.format(args)

    # Just copy all the files
    logging.info("*** (4/5) FILL INSTALL BLOCKDEVICE ***")
    copy_files_from_chroot(args)
    copy_files_other(args)

    # If user has a ssh pubkey, offer to copy it to device
    copy_ssh_key(args)
    pmb.chroot.shutdown(args, True)

    # Convert system image to sparse using img2simg
    if args.deviceinfo["flash_sparse"] == "true":
        logging.info("(native) make sparse system image")
        pmb.chroot.apk.install(args, ["libsparse"])
        sys_image = args.device + ".img"
        sys_image_sparse = args.device + "-sparse.img"
        pmb.chroot.user(args, ["img2simg", sys_image, sys_image_sparse],
                        working_dir="/home/user/rootfs/")
        pmb.chroot.user(args, ["mv", "-f", sys_image_sparse, sys_image],
                        working_dir="/home/user/rootfs/")

    # Kernel flash information
    logging.info("*** (5/5) FLASHING TO DEVICE ***")
    logging.info("Run the following to flash your installation to the"
                 " target device:")
    logging.info("* pmbootstrap flasher flash_kernel")
    logging.info("  Flashes the kernel + initramfs to your device:")
    logging.info("  " + args.work + "/chroot_rootfs_" + args.device +
                 "/boot")
    method = args.deviceinfo["flash_methods"]
    if (method in pmb.config.flashers and "boot" in
            pmb.config.flashers[method]["actions"]):
        logging.info("  (NOTE: " + method + " also supports booting"
                     " the kernel/initramfs directly without flashing."
                     " Use 'pmbootstrap flasher boot' to do that.)")

    # System flash information
    if not args.sdcard:
        logging.info("* pmbootstrap flasher flash_system")
        logging.info("  Flashes the system image, that has been"
                     " generated to your device:")
        logging.info("  " + args.work + "/chroot_native/home/user/rootfs/" +
                     args.device + ".img")
        logging.info("  (NOTE: This file has a partition table,"
                     " which contains a boot- and root subpartition.)")

    # Export information
    logging.info("* If the above steps do not work, you can also create"
                 " symlinks to the generated files with 'pmbootstrap export'"
                 " and flash outside of pmbootstrap.")


def install_recovery_zip(args):
    logging.info("*** (3/4) CREATING RECOVERY-FLASHABLE ZIP ***")
    suffix = "buildroot_" + args.deviceinfo["arch"]
    mount_device_rootfs(args, suffix)
    pmb.install.recovery.create_zip(args, suffix)

    # Flash information
    logging.info("*** (4/4) FLASHING TO DEVICE ***")
    logging.info("Run the following to flash your installation to the"
                 " target device:")
    logging.info("* pmbootstrap flasher --method adb sideload")
    logging.info("  Flashes the installer zip to your device:")

    # Export information
    logging.info("* If this does not work, you can also create a"
                 " symlink to the generated zip with 'pmbootstrap"
                 " export' and flash outside of pmbootstrap.")


def install(args):
    # Number of steps for the different installation methods.
    steps = 4 if args.android_recovery_zip else 5

    # Install required programs in native chroot
    logging.info("*** (1/{}) PREPARE NATIVE CHROOT ***".format(steps))
    pmb.chroot.apk.install(args, pmb.config.install_native_packages,
                           build=False)

    # List all packages to be installed (including the ones specified by --add)
    # and upgrade the installed packages/apkindexes
    logging.info('*** (2/{0}) CREATE DEVICE ROOTFS ("{1}") ***'.format(steps,
                 args.device))
    install_packages = (pmb.config.install_device_packages +
                        ["device-" + args.device])
    if args.ui.lower() != "none":
        install_packages += ["postmarketos-ui-" + args.ui]
    suffix = "rootfs_" + args.device
    pmb.chroot.apk.upgrade(args, suffix)

    # Explicitly call build on the install packages, to re-build them or any
    # dependency, in case the version increased
    if args.extra_packages.lower() != "none":
        install_packages += args.extra_packages.split(",")
    if args.add:
        install_packages += args.add.split(",")
    for pkgname in install_packages:
        pmb.build.package(args, pkgname, args.deviceinfo["arch"])

    # Install all packages to device rootfs chroot (and rebuild the initramfs,
    # because that doesn't always happen automatically yet, e.g. when the user
    # installed a hook without pmbootstrap - see #69 for more info)
    pmb.chroot.apk.install(args, install_packages, suffix)
    pmb.install.file.write_os_release(args, suffix)
    for flavor in pmb.chroot.other.kernel_flavors_installed(args, suffix):
        pmb.chroot.initfs.build(args, flavor, suffix)

    # Set the user password
    set_user_password(args)

    # Set the keymap if the device requires it
    setup_keymap(args)

    if args.android_recovery_zip:
        install_recovery_zip(args)
    else:
        install_system_image(args)
