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
import logging
import os

import pmb.build
import pmb.chroot.apk
import pmb.config
import pmb.helpers.run


def clone(args, name_repo, shallow=True, chown_to_user=False):
    # Check for repo name in the config
    if name_repo not in pmb.config.git_repos:
        raise ValueError("No git repository configured for " + name_repo)

    # Skip if already checked out
    if os.path.exists(args.work + "/cache_git/" + name_repo):
        return

    # Check out to temp folder
    name_temp = name_repo + ".temp"
    if not os.path.exists(args.work + "/cache_git/" + name_temp):
        # Set up chroot and install git
        pmb.chroot.apk.install(args, ["git"])
        logging.info("(native) git clone " + pmb.config.git_repos[name_repo])

        # git options
        options = []
        if shallow:
            options += ["--depth=1"]

        # Run the command
        pmb.chroot.user(args, ["git", "clone"] + options +
                              [pmb.config.git_repos[name_repo], name_temp],
                        working_dir="/home/pmos/git/", check=False,
                        output="stdout")
        if not os.path.exists(args.work + "/cache_git/" + name_temp):
            logging.info("NOTE: cloning from git is known to fail when the"
                         " host linux kernel is older than 3.17:"
                         " <https://postmarketos.org/oldkernel>")
            raise RuntimeError("git clone failed!")

    # Chown to user's UID and GID
    if chown_to_user:
        uid_gid = "{}:{}".format(os.getuid(), os.getgid())
        pmb.helpers.run.root(args, ["chown", "-R", uid_gid, args.work +
                                    "/cache_git/" + name_temp])

    # Rename the temp folder
    pmb.helpers.run.root(args, ["mv", name_temp, name_repo],
                         args.work + "/cache_git")


def rev_parse(args, revision="HEAD"):
    rev = pmb.helpers.run.user(args, ["git", "rev-parse", revision],
                               args.aports, output_return=True, check=False)
    if rev is None:
        logging.warning("WARNING: Failed to determine revision of git repository at " + args.aports)
        return ""
    return rev.rstrip()
