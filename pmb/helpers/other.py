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
import os
import logging
import pmb.chroot
import pmb.config
import pmb.helpers.run


def folder_size(args, path):
    """
    Run `du` to calculate the size of a folder (this is less code and
    faster than doing the same task in pure Python). This result is only
    approximatelly right, but good enough for pmbootstrap's use case:
    <https://github.com/postmarketOS/pmbootstrap/pull/760>

    :returns: folder size in bytes
    """
    output = pmb.helpers.run.root(args, ["du", "--summarize",
                                         "--apparent-size",
                                         "--block-size=1",
                                         path], return_stdout=True)
    ret = int(output.split("\t")[0])
    return ret


def check_grsec(args):
    """
    Check if the current kernel is based on the grsec patchset, and if
    the chroot_deny_chmod option is enabled. Raise an exception in that
    case, with a link to the issue. Otherwise, do nothing.
    """
    path = "/proc/sys/kernel/grsecurity/chroot_deny_chmod"
    if not os.path.exists(path):
        return

    link = "https://github.com/postmarketOS/pmbootstrap/issues/107"
    raise RuntimeError("You're running a kernel based on the grsec"
                       " patchset. At the moment, pmbootstrap is not"
                       " compatible with grsec or a hardened kernel, sorry!"
                       " To get pmbootstrap working, you will need to switch"
                       " to a vanilla kernel (i.e. non-hardened and without grsec)."
                       " Alternatively, it would be awesome if you want to add"
                       " support for hardened/grsec kernels, please see this for"
                       " more details: <" + link + ">")


def migrate_success(args):
    logging.info("Migration done")
    with open(args.work + "/version", "w") as handle:
        handle.write(pmb.config.work_version + "\n")


def migrate_work_folder(args):
    # Read current version
    current = "0"
    path = args.work + "/version"
    if os.path.exists(path):
        with open(path, "r") as f:
            current = f.read().rstrip()

    # Compare version, print warning or do nothing
    required = pmb.config.work_version
    if current == required:
        return
    logging.info("WARNING: Your work folder version needs to be migrated"
                 " (from version " + current + " to " + required + ")!")

    # 0 => 1
    if current == "0" and required == "1":
        # Ask for confirmation
        logging.info("Changelog:")
        logging.info("* Building chroots have a different username: "
                     "<https://github.com/postmarketOS/pmbootstrap/issues/709>")
        logging.info("Migration will do the following:")
        logging.info("* Zap your chroots")
        logging.info("* Adjust '" + args.work + "/config_abuild/abuild.conf'")
        if not pmb.helpers.cli.confirm(args):
            raise RuntimeError("Aborted.")

        # Zap and update abuild.conf
        pmb.chroot.zap(args, False)
        conf = args.work + "/config_abuild/abuild.conf"
        if os.path.exists(conf):
            pmb.helpers.run.root(args, ["sed", "-i",
                                        "s./home/user/./home/pmos/.g", conf])
        # Update version file
        migrate_success(args)
        return

    # Can't migrate, user must delete it
    raise RuntimeError("Sorry, we can't migrate that automatically. Please run"
                       " 'pmbootstrap shutdown', then delete your current work"
                       " folder manually ('sudo rm -rf " + args.work +
                       "') and start over with 'pmbootstrap init'. All your"
                       " binary packages will be lost.")
