"""
Copyright 2018 Pablo Castellano

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
import signal
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
    path = args.work + "/chroot_native/home/pmos/rootfs/" + device + ".img"
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


def which_spice(args):
    """
    Finds some SPICE executable or raises an exception otherwise
    :returns: path_to_spice_executable or None
    """
    executables = ["remote-viewer", "spicy"]
    for executable in executables:
        if shutil.which(executable):
            return executable
    return None


def command_spice(args):
    """
    Generate the full SPICE command with arguments connect to the virtual
    machine
    :returns: None or list with the spice command, e.g.:
              ["spicy", "-h", "127.0.0.1", "-p", "8077"]
    """
    if not args.spice_port:
        return None

    spice_binary = which_spice(args)
    if not spice_binary:
        logging.warning("WARNING: Could not find any SPICE client (spicy,"
                        " remote-viewer) in your PATH, starting without"
                        " SPICE support!")
        return None

    if spice_binary == "spicy":
        return ["spicy", "-h", "127.0.0.1", "-p", args.spice_port]
    return ["remote-viewer", "spice://127.0.0.1?port=" + args.spice_port]


def command_qemu(args, arch, device, img_path, spice_enabled):
    """
    Generate the full qemu command with arguments to run postmarketOS
    """
    qemu_bin = which_qemu(args, arch)
    deviceinfo = pmb.parse.deviceinfo(args, device=device)
    cmdline = deviceinfo["kernel_cmdline"]
    if args.cmdline:
        cmdline = args.cmdline
    logging.debug("Kernel cmdline: " + cmdline)

    port_ssh = str(args.port)
    port_telnet = str(args.port + 1)

    suffix = "rootfs_" + device
    rootfs = args.work + "/chroot_" + suffix
    flavor = pmb.chroot.other.kernel_flavor_autodetect(args, suffix)
    command = [qemu_bin]
    command += ["-kernel", rootfs + "/boot/vmlinuz-" + flavor]
    command += ["-initrd", rootfs + "/boot/initramfs-" + flavor]
    command += ["-append", '"' + cmdline + '"']
    command += ["-m", str(args.memory)]
    command += ["-netdev",
                "user,id=net0,"
                "hostfwd=tcp::" + port_ssh + "-:22,"
                "hostfwd=tcp::" + port_telnet + "-:23"
                ",net=172.16.42.0/24,dhcpstart=" + pmb.config.default_ip
                ]
    command += ["-show-cursor"]

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

        # Add storage
        command += ["-device", "virtio-blk-device,drive=system"]
        command += ["-drive", "if=none,id=system,file={},id=hd0".format(img_path)]

    else:
        raise RuntimeError("Architecture {} not supported by this command yet.".format(arch))

    # Kernel Virtual Machine (KVM) support
    native = True
    if args.arch:
        arch1 = pmb.parse.arch.uname_to_qemu(args.arch_native)
        arch2 = pmb.parse.arch.uname_to_qemu(args.arch)
        native = (arch1 == arch2)
    if native and os.path.exists("/dev/kvm"):
        command += ["-enable-kvm"]
    else:
        logging.info("WARNING: Qemu is not using KVM and will run slower!")

    # 2D acceleration support via QXL/SPICE or virtio
    if spice_enabled:
        command += ["-vga", "qxl"]
        command += ["-spice",
                    "port=" + args.spice_port + ",addr=127.0.0.1" +
                    ",disable-ticketing"]
    else:
        if native and args.qemu_native_mesa_driver == "dri-virtio":
            command += ["-vga", "virtio"]
        command += ["-display", args.qemu_display]

    return command


def resize_image(args, img_size_new, img_path):
    """
    Truncates the system image to a specific size. The value must be larger than the
    current image size, and it must be specified in MiB or GiB units (powers of 1024).

    :param img_size_new: new image size in M or G
    :param img_path: the path to the system image
    """
    # Current image size in bytes
    img_size = os.path.getsize(img_path)

    # Make sure we have at least 1 integer followed by either M or G
    pattern = re.compile("^[0-9]+[M|G]$")
    if not pattern.match(img_size_new):
        raise RuntimeError("You must specify the system image size in [M]iB or [G]iB, e.g. 2048M or 2G")

    # Remove M or G and convert to bytes
    img_size_new_bytes = int(img_size_new[:-1]) * 1024 * 1024

    # Convert further for G
    if (img_size_new[-1] == "G"):
        img_size_new_bytes = img_size_new_bytes * 1024

    if (img_size_new_bytes >= img_size):
        logging.info("Setting the system image size to " + img_size_new)
        pmb.helpers.run.root(args, ["truncate", "-s", img_size_new, img_path])
    else:
        # Convert to human-readable format
        # NOTE: We convert to M here, and not G, so that we don't have to display
        # a size like 1.25G, since decimal places are not allowed by truncate.
        # We don't want users thinking they can use decimal numbers, and so in
        # this example, they would need to use a size greater then 1280M instead.
        img_size_str = str(round(img_size / 1024 / 1024)) + "M"

        raise RuntimeError("The system image size must be " + img_size_str + " or greater")


def sigterm_handler(number, frame):
    raise RuntimeError("pmbootstrap was terminated by another process,"
                       " and killed the Qemu VM it was running.")


def run(args):
    """
    Run a postmarketOS image in qemu
    """
    # Get arch, device, img_path
    arch = pmb.parse.arch.uname_to_qemu(args.arch_native)
    if args.arch:
        arch = pmb.parse.arch.uname_to_qemu(args.arch)
    device = pmb.parse.arch.qemu_to_pmos_device(arch)
    img_path = system_image(args, device)
    logging.info("Running postmarketOS in QEMU VM (" + arch + ")")

    # Get the Qemu and spice commands
    spice = command_spice(args)
    spice_enabled = True if spice else False
    qemu = command_qemu(args, arch, device, img_path, spice_enabled)

    # Workaround: Qemu runs as local user and needs write permissions in the
    # system image, which is owned by root
    if not os.access(img_path, os.W_OK):
        pmb.helpers.run.root(args, ["chmod", "666", img_path])

    # Resize the system image (or show hint)
    if args.image_size:
        resize_image(args, args.image_size, img_path)
    else:
        logging.info("NOTE: Run 'pmbootstrap qemu --image-size 2G' to set"
                     " the system image size when you run out of space!")

    # SSH/telnet hints
    logging.info("Connect to the VM (telnet requires 'pmbootstrap initfs"
                 " hook_add debug-shell'):")
    logging.info("* (ssh) ssh -p {port} {user}@localhost".format(**vars(args)))
    logging.info("* (telnet) telnet localhost " + str(args.port + 1))

    # Run Qemu (or Qemu + SPICE) and kill it together with pmbootstrap
    process = None
    try:
        signal.signal(signal.SIGTERM, sigterm_handler)
        process = pmb.helpers.run.user(args, qemu, background=spice_enabled)
        if spice:
            pmb.helpers.run.user(args, spice)
    except KeyboardInterrupt:
        # Don't show a trace when pressing ^C
        pass
    finally:
        if process:
            process.terminate()
