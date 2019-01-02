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
import glob
import logging

import pmb.config
import pmb.chroot.apk


def list_chroot(args, suffix, remove_prefix=True):
    ret = []
    prefix = pmb.config.initfs_hook_prefix
    for pkgname in pmb.chroot.apk.installed(args, suffix).keys():
        if pkgname.startswith(prefix):
            if remove_prefix:
                ret.append(pkgname[len(prefix):])
            else:
                ret.append(pkgname)
    return ret


def list_aports(args):
    ret = []
    prefix = pmb.config.initfs_hook_prefix
    for path in glob.glob(args.aports + "/*/" + prefix + "*"):
        ret.append(os.path.basename(path)[len(prefix):])
    return ret


def ls(args, suffix):
    hooks_chroot = list_chroot(args, suffix)
    hooks_aports = list_aports(args)

    for hook in hooks_aports:
        line = "* " + hook
        if hook in hooks_chroot:
            line += " (installed)"
        else:
            line += " (not installed)"
        logging.info(line)


def add(args, hook, suffix):
    if hook not in list_aports(args):
        raise RuntimeError("Invalid hook name! Run 'pmbootstrap initfs hook_ls'"
                           " to get a list of all hooks.")
    prefix = pmb.config.initfs_hook_prefix
    pmb.chroot.apk.install(args, [prefix + hook], suffix)


def delete(args, hook, suffix):
    if hook not in list_chroot(args, suffix):
        raise RuntimeError("There is no such hook installed!")
    prefix = pmb.config.initfs_hook_prefix
    pmb.chroot.root(args, ["apk", "del", prefix + hook], suffix)


def update(args, suffix):
    """
    Rebuild and update all hooks, that are out of date
    """
    pmb.chroot.apk.install(args, list_chroot(args, suffix, False), suffix)
