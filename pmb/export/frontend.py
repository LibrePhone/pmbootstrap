import logging
import os

import pmb.helpers.run
import pmb.helpers.frontend
import pmb.chroot.initfs
import pmb.export


def frontend(args):
    # Create the export folder
    target = args.export_folder
    if not os.path.exists(target):
        pmb.helpers.run.user(args, ["mkdir", "-p", target])

    # System image note
    img_path = "/home/user/rootfs/" + args.device + ".img"
    if not os.path.exists(args.work + "/chroot_native" + img_path):
        logging.info("NOTE: To export the system image, run 'pmbootstrap"
                     " install' first (without the 'sdcard' parameter).")

    # Rebuild the initramfs, just to make sure (see #69)
    flavor = pmb.helpers.frontend._parse_flavor(args)
    pmb.chroot.initfs.build(args, flavor, "rootfs_" + args.device)

    # Do the export, print all files
    logging.info("Export symlinks to: " + target)
    if args.odin_flashable_tar:
        pmb.export.odin(args, flavor, target)
    pmb.export.symlinks(args, flavor, target)
