"""
Copyright 2017 Pablo Castellano

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
import shutil

import pmb.build
import pmb.chroot
import pmb.chroot.apk
import pmb.chroot.other
import pmb.chroot.initfs
import pmb.config
import pmb.helpers.devices
import pmb.helpers.run
import pmb.parse.arch


def system_image(args, device):
    """
    Returns path to system image for specified device. In case that it doesn't
    exist, raise and exception explaining how to generate it.
    """
    path = args.work + "/chroot_native/home/user/rootfs/" + device + ".img"
    if not os.path.exists(path):
        logging.debug("Could not find system image: " + path)
        img_command = "pmbootstrap install"
        if device != args.device:
            img_command = ("pmbootstrap config device " + device +
                           "' and '" + img_command)
        message = "The system image '{0}' has not been generated yet, please" \
                  " run '{1}' first.".format(device, img_command)
        raise RuntimeError(message)
    return path


def which_qemu(args, arch):
    """
    Finds the qemu executable or raises an exception otherwise
    """
    executable = "qemu-system-" + arch
    if shutil.which(executable):
        return executable
    else:
        raise RuntimeError("Could not find the '" + executable + "' executable"
                           " in your PATH. Please install it in order to"
                           " run qemu.")


def qemu_command(args, arch, device, img_path):
    """
    Generate the full qemu command with arguments to run postmarketOS
    """
    qemu_bin = which_qemu(args, arch)
    deviceinfo = pmb.parse.deviceinfo(args, device=device)
    cmdline = deviceinfo["kernel_cmdline"]
    if args.cmdline:
        cmdline = args.cmdline
    logging.info("cmdline: " + cmdline)

    ssh_port = str(args.port)
    telnet_port = str(args.port + 1)
    telnet_debug_port = str(args.port + 2)

    rootfs = args.work + "/chroot_rootfs_" + device
    command = [qemu_bin]
    command += ["-kernel", rootfs + "/boot/vmlinuz-postmarketos"]
    command += ["-initrd", rootfs + "/boot/initramfs-postmarketos"]
    command += ["-append", '"' + cmdline + '"']
    command += ["-m", str(args.memory)]
    command += ["-netdev",
                "user,id=net0,"
                "hostfwd=tcp::" + ssh_port + "-:22,"
                "hostfwd=tcp::" + telnet_port + "-:23,"
                "hostfwd=tcp::" + telnet_debug_port + "-:24"
                ",net=172.16.42.0/24,dhcpstart=" + pmb.config.default_ip
                ]

    if deviceinfo["dtb"] != "":
        dtb_image = rootfs + "/usr/share/dtb/" + deviceinfo["dtb"] + ".dtb"
        if not os.path.exists(dtb_image):
            raise RuntimeError("DTB file not found: " + dtb_image)
        command += ["-dtb", dtb_image]

    if arch == "x86_64":
        command += ["-serial", "stdio"]
        command += ["-drive", "file=" + img_path + ",format=raw"]
        command += ["-device", "e1000,netdev=net0"]

    elif arch == "arm":
        command += ["-M", "vexpress-a9"]
        command += ["-sd", img_path]
        command += ["-device", "virtio-net-device,netdev=net0"]

    elif arch == "aarch64":
        command += ["-M", "virt"]
        command += ["-cpu", "cortex-a57"]
        command += ["-device", "virtio-gpu-pci"]
        command += ["-device", "virtio-net-device,netdev=net0"]

        # add storage
        command += ["-device", "virtio-blk-device,drive=system"]
        command += ["-drive", "if=none,id=system,file={},id=hd0".format(img_path)]

    else:
        raise RuntimeError("Architecture {} not supported by this command yet.".format(arch))

    # Kernel Virtual Machine (KVM) support
    enable_kvm = True
    if args.arch:
        arch1 = pmb.parse.arch.uname_to_qemu(args.arch_native)
        arch2 = pmb.parse.arch.uname_to_qemu(args.arch)
        enable_kvm = (arch1 == arch2)
    if enable_kvm and os.path.exists("/dev/kvm"):
        command += ["-enable-kvm"]
    else:
        logging.info("Warning: qemu is not using KVM and will run slower!")

    return command


def run(args):
    """
    Run a postmarketOS image in qemu
    """
    arch = pmb.parse.arch.uname_to_qemu(args.arch_native)
    if args.arch:
        arch = pmb.parse.arch.uname_to_qemu(args.arch)
    logging.info("Running postmarketOS in QEMU VM (" + arch + ")")

    device = pmb.parse.arch.qemu_to_pmos_device(arch)
    img_path = system_image(args, device)

    # Workaround: qemu runs as local user and needs write permissions in the
    # system image, which is owned by root
    if not os.access(img_path, os.W_OK):
        pmb.helpers.run.root(args, ["chmod", "666", img_path])

    command = qemu_command(args, arch, device, img_path)

    logging.info("Command: " + " ".join(command))
    print()
    logging.info("You can connect to the Virtual Machine using the"
                 " following services:")
    logging.info("(ssh) ssh -p " + str(args.port) + " user@localhost")
    logging.info("(telnet) telnet localhost " + str(args.port + 1))
    logging.info("(telnet debug) telnet localhost " + str(args.port + 2))
    pmb.helpers.run.user(args, command)
