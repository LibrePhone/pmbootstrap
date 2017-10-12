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

import pmb.build
import pmb.chroot.apk
import pmb.config
import pmb.helpers.run


def clone(args, repo_name):
    if repo_name not in pmb.config.git_repos:
        raise ValueError("No git repository configured for " + repo_name)

    if not os.path.exists(args.work + "/cache_git/" + repo_name):
        pmb.chroot.apk.install(args, ["git"])
        logging.info("(native) git clone " + pmb.config.git_repos[repo_name])
        pmb.chroot.user(args, ["git", "clone", "--depth=1",
                               pmb.config.git_repos[repo_name], repo_name], working_dir="/home/pmos/git/")


def rev_parse(args, revision="HEAD"):
    rev = pmb.helpers.run.user(args, ["git", "rev-parse", revision],
                               working_dir=args.aports,
                               return_stdout=True,
                               check=False)
    if rev is None:
        logging.warning("WARNING: Failed to determine revision of git repository at " + args.aports)
        return ""
    return rev.rstrip()


def find_out_of_sync_files_tracked(args, git_root):
    """
    Find all files tracked by git, that are are out of sync with origin/HEAD.

    In some cases (when you rename a remote or add it manually), origin/HEAD
    does not exist. We check for that to provide a meaningful error message
    instead of a confusing crash (see #151).
    See also: <https://stackoverflow.com/a/17639471>
    """
    # Return changed files compared to origin/HEAD when it exists
    ret = pmb.helpers.run.user(args, ["git", "show-ref",
                                      "refs/remotes/origin/HEAD"],
                               working_dir=git_root, return_stdout=True,
                               check=False)
    if ret and "refs/remotes/origin/HEAD" in ret:
        return pmb.helpers.run.user(args, ["git", "diff", "--name-only",
                                           "origin"], working_dir=git_root,
                                    return_stdout=True)

    # Meaningful error
    logging.debug("Output of 'git diff --name-only origin': " + str(ret))
    logging.info("See also: <https://github.com/postmarketOS/pmbootstrap/"
                 "issues/151>")
    fix_cmds = ("git symbolic-ref refs/remotes/origin/HEAD refs/remotes/"
                "origin/master; git fetch")
    raise RuntimeError("Your aports repository does not have the"
                       " 'origin/HEAD' reference. Please add it by"
                       " running the following commands inside " +
                       git_root + ": " + fix_cmds)
