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
import logging
import os
import re
import glob
import shlex

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
    Calculate the size of the boot and root subpartition.

    :returns: (boot, root) the size of the boot and root
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

    # Add some free space, see also: #336, #1671
    full *= 1.20
    full += 50 * 1024 * 1024
    boot += 25 * 1024 * 1024
    return (boot, full - boot)


def get_nonfree_packages(args, device):
    """
    Get the non-free packages based on user's choice in "pmbootstrap init" and
    based on whether there are non-free packages in the APKBUILD or not.

    :returns: list of non-free packages to be installed. Example:
              ["device-nokia-n900-nonfree-firmware"]
    """
    # Read subpackages
    apkbuild_path = args.aports + "/device/device-" + device + "/APKBUILD"
    apkbuild = pmb.parse.apkbuild(args, apkbuild_path)
    subpackages = apkbuild["subpackages"]

    # Check for firmware and userland
    ret = []
    prefix = "device-" + device + "-nonfree-"
    if args.nonfree_firmware and prefix + "firmware" in subpackages:
        ret += [prefix + "firmware"]
    if args.nonfree_userland and prefix + "userland" in subpackages:
        ret += [prefix + "userland"]
    return ret


def get_kernel_package(args, device):
    """
    Get the device's kernel subpackage based on the user's choice in
    "pmbootstrap init".

    :param device: code name, e.g. "sony-amami"
    :returns: [] or the package in a list, e.g.
              ["device-sony-amami-kernel-mainline"]
    """
    # Empty list: single kernel devices / "none" selected
    kernels = pmb.parse._apkbuild.kernels(args, device)
    if not kernels or args.kernel == "none":
        return []

    # Sanity check
    if args.kernel not in kernels:
        raise RuntimeError("Selected kernel (" + args.kernel + ") is not"
                           " configured for device " + device + ". Please"
                           " run 'pmbootstrap init' to select a valid kernel.")

    # Selected kernel subpackage
    return ["device-" + device + "-kernel-" + args.kernel]


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

    # Update or copy all files
    if args.rsync:
        pmb.chroot.apk.install(args, ["rsync"])
        rsync_flags = "-a"
        if args.verbose:
            rsync_flags += "vP"
        pmb.chroot.root(args, ["rsync", rsync_flags, "--delete"] + folders + ["/mnt/install/"],
                        working_dir=mountpoint)
        pmb.chroot.root(args, ["rm", "-rf", "/mnt/install/home"])
    else:
        pmb.chroot.root(args, ["cp", "-a"] + folders + ["/mnt/install/"],
                        working_dir=mountpoint)


def create_home_from_skel(args):
    """
    Create /home/{user} from /etc/skel
    """
    rootfs = args.work + "/chroot_native/mnt/install"
    homedir = rootfs + "/home/" + args.user
    pmb.helpers.run.root(args, ["mkdir", rootfs + "/home"])
    pmb.helpers.run.root(args, ["cp", "-a", rootfs + "/etc/skel", homedir])
    pmb.helpers.run.root(args, ["chown", "-R", "10000", homedir])


def configure_apk(args):
    """
    Copies over all keys used locally to compile packages, and disables the
    /mnt/pmbootstrap-packages repository.
    """
    # Copy over keys
    rootfs = args.work + "/chroot_native/mnt/install"
    for key in glob.glob(args.work + "/config_apk_keys/*.pub"):
        pmb.helpers.run.root(args, ["cp", key, rootfs + "/etc/apk/keys/"])

    # Disable pmbootstrap repository
    pmb.helpers.run.root(args, ["sed", "-i", "/\/mnt\/pmbootstrap-packages/d",
                                rootfs + "/etc/apk/repositories"])
    pmb.helpers.run.user(args, ["cat", rootfs + "/etc/apk/repositories"])


def set_user(args):
    """
    Create user with UID 10000 if it doesn't exist.
    Usually the ID for the first user created is 1000, but higher ID is
    chosen here to avoid conflict with Android UIDs/GIDs.

    """
    suffix = "rootfs_" + args.device
    if not pmb.chroot.user_exists(args, args.user, suffix):
        pmb.chroot.root(args, ["adduser", "-D", "-u", "10000", args.user],
                        suffix)
        for group in pmb.config.install_user_groups:
            pmb.chroot.root(args, ["addgroup", "-S", group], suffix,
                            check=False)
            pmb.chroot.root(args, ["addgroup", args.user, group], suffix)


def setup_login(args):
    """
    Loop until the password for user has been set successfully, and disable root
    login.
    """
    # User password
    logging.info(" *** SET LOGIN PASSWORD FOR: '" + args.user + "' ***")
    suffix = "rootfs_" + args.device
    while True:
        try:
            pmb.chroot.root(args, ["passwd", args.user], suffix,
                            output="interactive")
            break
        except RuntimeError:
            logging.info("WARNING: Failed to set the password. Try it"
                         " one more time.")
            pass

    # Disable root login
    pmb.chroot.root(args, ["passwd", "-l", "root"], suffix)


def copy_ssh_keys(args):
    """
    If requested, copy user's SSH public keys to the device if they exist
    """
    if not args.ssh_keys:
        return
    keys = []
    for key in glob.glob(os.path.expanduser("~/.ssh/id_*.pub")):
        with open(key, "r") as infile:
            keys += infile.readlines()

    if not len(keys):
        logging.info("NOTE: Public SSH keys not found. Since no SSH keys " +
                     "were copied, you will need to use SSH password authentication!")
        return

    authorized_keys = args.work + "/chroot_native/tmp/authorized_keys"
    outfile = open(authorized_keys, "w")
    for key in keys:
        outfile.write("%s" % key)
    outfile.close()

    target = args.work + "/chroot_native/mnt/install/home/" + args.user + "/.ssh"
    pmb.helpers.run.root(args, ["mkdir", target])
    pmb.helpers.run.root(args, ["chmod", "700", target])
    pmb.helpers.run.root(args, ["cp", authorized_keys, target + "/authorized_keys"])
    pmb.helpers.run.root(args, ["rm", authorized_keys])
    pmb.helpers.run.root(args, ["chown", "-R", "10000:10000", target])


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
        pmb.chroot.root(args, ["setup-keymap", layout, variant], suffix,
                        output="interactive")
    else:
        logging.info("NOTE: No valid keymap specified for device")


def setup_hostname(args):
    """
    Set the hostname and update localhost address in /etc/hosts
    """
    # Default to device name
    hostname = args.hostname
    if not hostname:
        hostname = args.device

    if not pmb.helpers.other.validate_hostname(hostname):
        raise RuntimeError("Hostname '" + hostname + "' is not valid, please"
                           " run 'pmbootstrap init' to configure it.")

    # Update /etc/hosts
    suffix = "rootfs_" + args.device
    pmb.chroot.root(args, ["sh", "-c", "echo " + shlex.quote(hostname) +
                           " > /etc/hostname"], suffix)
    regex = ("s/^127\.0\.0\.1.*/127.0.0.1\t" + re.escape(hostname) +
             " localhost.localdomain localhost/")
    pmb.chroot.root(args, ["sed", "-i", "-e", regex, "/etc/hosts"], suffix)


def embed_firmware(args):
    """
    This method will embed firmware, located at /usr/share, that are specified
    by the "sd_embed_firmware" deviceinfo parameter into the SD card image
    (e.g. u-boot). Binaries that would overwrite the first partition are not
    accepted, and if multiple binaries are specified then they will be checked
    for collisions with each other.
    """
    if not args.deviceinfo["sd_embed_firmware"]:
        return

    step = 1024
    if args.deviceinfo["sd_embed_firmware_step_size"]:
        try:
            step = int(args.deviceinfo["sd_embed_firmware_step_size"])
        except ValueError:
            raise RuntimeError("Value for "
                               "deviceinfo_sd_embed_firmware_step_size "
                               "is not valid: {}".format(step))

    device_rootfs = mount_device_rootfs(args)
    binaries = args.deviceinfo["sd_embed_firmware"].split(",")

    # Perform three checks prior to writing binaries to disk: 1) that binaries
    # exist, 2) that binaries do not extend into the first partition, 3) that
    # binaries do not overlap eachother
    binary_ranges = {}
    binary_list = []
    for binary_offset in binaries:
        binary, offset = binary_offset.split(':')
        try:
            offset = int(offset)
        except ValueError:
            raise RuntimeError("Value for firmware binary offset is "
                               "not valid: {}".format(offset))
        binary_path = os.path.join(args.work, "chroot_rootfs_" +
                                   args.device, "usr/share", binary)
        if not os.path.exists(binary_path):
            raise RuntimeError("The following firmware binary does not "
                               "exist in the device rootfs: "
                               "{}".format("/usr/share/" + binary))
        # Insure that embedding the firmware will not overrun the
        # first partition
        max_size = (2048 * 512) - (offset * step)
        binary_size = os.path.getsize(binary_path)
        if binary_size > max_size:
            raise RuntimeError("The firmware is too big to embed in the "
                               "disk image {}B > {}B".format(binary_size,
                                                             max_size))
        # Insure that the firmware does not conflict with any other firmware
        # that will be embedded
        binary_start = offset * step
        binary_end = binary_start + binary_size
        for start, end in binary_ranges.items():
            if ((binary_start >= start and binary_start <= end) or
                    (binary_end >= start and binary_end <= end)):
                raise RuntimeError("The firmware overlaps with at least one "
                                   "other firmware image: {}".format(binary))
        binary_ranges[binary_start] = binary_end
        binary_list.append((binary, offset))

    # Write binaries to disk
    for binary, offset in binary_list:
        binary_file = os.path.join("/usr/share", binary)
        logging.info("Embed firmware {} in the SD card image at offset {} with"
                     " step size {}".format(binary, offset, step))
        filename = os.path.join(device_rootfs, binary_file.lstrip("/"))
        pmb.chroot.root(args, ["dd", "if=" + filename, "of=/dev/install",
                               "bs=" + str(step), "seek=" + str(offset)])


def sanity_check_sdcard(device):
    device_name = os.path.basename(device)
    if os.path.isdir('/sys/class/block/{}'.format(device_name)):
        with open('/sys/class/block/{}/ro'.format(device_name), 'r') as handle:
            ro = handle.read()
        if ro == '1\n':
            raise RuntimeError("{} is read-only, Is the sdcard locked?".format(device))


def install_system_image(args):
    # Partition and fill image/sdcard
    logging.info("*** (3/5) PREPARE INSTALL BLOCKDEVICE ***")
    pmb.chroot.shutdown(args, True)
    (size_boot, size_root) = get_subpartitions_size(args)
    if not args.rsync:
        pmb.install.blockdevice.create(args, size_boot, size_root)
        if not args.split:
            pmb.install.partition(args, size_boot)
    if not args.split:
        pmb.install.partitions_mount(args)

    if args.full_disk_encryption:
        logging.info("WARNING: Full disk encryption is enabled!")
        logging.info("Make sure that osk-sdl has been properly configured for your device")
        logging.info("or else you will be unable to unlock the rootfs on boot!")
        logging.info("If you started a device port, it is recommended you disable")
        logging.info("FDE by re-running the install command with '--no-fde' until")
        logging.info("you have properly configured osk-sdl. More information:")
        logging.info("<https://postmarketos.org/osk-port>")
    pmb.install.format(args)

    # Just copy all the files
    logging.info("*** (4/5) FILL INSTALL BLOCKDEVICE ***")
    copy_files_from_chroot(args)
    create_home_from_skel(args)
    configure_apk(args)
    copy_ssh_keys(args)
    embed_firmware(args)
    pmb.chroot.shutdown(args, True)

    # Convert rootfs to sparse using img2simg
    if args.deviceinfo["flash_sparse"] == "true" and not args.split:
        logging.info("(native) make sparse rootfs")
        pmb.chroot.apk.install(args, ["libsparse"])
        sys_image = args.device + ".img"
        sys_image_sparse = args.device + "-sparse.img"
        pmb.chroot.user(args, ["img2simg", sys_image, sys_image_sparse],
                        working_dir="/home/pmos/rootfs/")
        pmb.chroot.user(args, ["mv", "-f", sys_image_sparse, sys_image],
                        working_dir="/home/pmos/rootfs/")

    # Kernel flash information
    logging.info("*** (5/5) FLASHING TO DEVICE ***")
    logging.info("Run the following to flash your installation to the"
                 " target device:")

    # System flash information
    if not args.sdcard and not args.split:
        logging.info("* pmbootstrap flasher flash_rootfs")
        logging.info("  Flashes the generated rootfs image to your device:")
        logging.info("  " + args.work + "/chroot_native/home/pmos/rootfs/" +
                     args.device + ".img")
        logging.info("  (NOTE: This file has a partition table, which contains"
                     " /boot and / subpartitions. That way we don't need to"
                     " change the partition layout on your device.)")

    logging.info("* pmbootstrap flasher flash_kernel")
    logging.info("  Flashes the kernel + initramfs to your device:")
    logging.info("  " + args.work + "/chroot_rootfs_" + args.device +
                 "/boot")
    method = args.deviceinfo["flash_method"]
    if (method in pmb.config.flashers and "boot" in
            pmb.config.flashers[method]["actions"]):
        logging.info("  (NOTE: " + method + " also supports booting"
                     " the kernel/initramfs directly without flashing."
                     " Use 'pmbootstrap flasher boot' to do that.)")

    # Export information
    if args.split:
        logging.info("* Boot and root image files have been generated, run"
                     " 'pmbootstrap export' to create symlinks and flash"
                     " outside of pmbootstrap.")
    else:
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
    logging.info("Flashing with the recovery zip is explained here:")
    logging.info("<https://postmarketos.org/recoveryzip>")


def install(args):
    # Sanity checks
    if not args.android_recovery_zip and args.sdcard:
        sanity_check_sdcard(args.sdcard)

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
                        ["device-" + args.device] +
                        get_kernel_package(args, args.device) +
                        get_nonfree_packages(args, args.device))
    if args.ui.lower() != "none":
        install_packages += ["postmarketos-ui-" + args.ui]
    suffix = "rootfs_" + args.device
    pmb.chroot.apk.upgrade(args, suffix)

    # Create final user and remove 'build' user
    set_user(args)

    # Explicitly call build on the install packages, to re-build them or any
    # dependency, in case the version increased
    if args.extra_packages.lower() != "none":
        install_packages += args.extra_packages.split(",")
    if args.add:
        install_packages += args.add.split(",")
    if args.device.startswith("qemu-"):
        install_packages += ["mesa-" + args.qemu_native_mesa_driver]
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
    setup_login(args)

    # Set the keymap if the device requires it
    setup_keymap(args)

    # Set timezone
    pmb.chroot.root(args, ["setup-timezone", "-z", args.timezone], suffix)

    # Set the hostname as the device name
    setup_hostname(args)

    if args.android_recovery_zip:
        install_recovery_zip(args)
    else:
        install_system_image(args)
