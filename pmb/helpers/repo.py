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

"""
Functions that work on both (binary package) repos. See also:
- pmb/helpers/pmaports.py (work on pmaports)
- pmb/helpers/package.py (work on both)
"""

import os
import hashlib
import logging
import pmb.helpers.http
import pmb.helpers.run


def hash(url, length=8):
    """
    Generate the hash, that APK adds to the APKINDEX and apk packages
    in its apk cache folder. It is the "12345678" part in this example:
    "APKINDEX.12345678.tar.gz".

    :param length: The length of the hash in the output file.

    See also: official implementation in apk-tools:
    <https://git.alpinelinux.org/cgit/apk-tools/>

    blob.c: apk_blob_push_hexdump(), "const char *xd"
    apk_defines.h: APK_CACHE_CSUM_BYTES
    database.c: apk_repo_format_cache_index()
    """
    binary = hashlib.sha1(url.encode("utf-8")).digest()
    xd = "0123456789abcdefghijklmnopqrstuvwxyz"
    csum_bytes = int(length / 2)

    ret = ""
    for i in range(csum_bytes):
        ret += xd[(binary[i] >> 4) & 0xf]
        ret += xd[binary[i] & 0xf]

    return ret


def urls(args, user_repository=True, postmarketos_mirror=True):
    """
    Get a list of repository URLs, as they are in /etc/apk/repositories.
    """
    ret = []
    # Local user repository (for packages compiled with pmbootstrap)
    if user_repository:
        ret.append("/mnt/pmbootstrap-packages")

    # Upstream postmarketOS binary repository
    if postmarketos_mirror:
        for mirror in args.mirrors_postmarketos:
            ret.append(mirror)

    # Upstream Alpine Linux repositories
    directories = ["main", "community"]
    if args.alpine_version == "edge":
        directories.append("testing")
    for dir in directories:
        ret.append(args.mirror_alpine + args.alpine_version + "/" + dir)
    return ret


def apkindex_files(args, arch=None):
    """
    Get a list of outside paths to all resolved APKINDEX.tar.gz files for a
    specific arch.
    :param arch: defaults to native
    """
    if not arch:
        arch = args.arch_native

    # Local user repository (for packages compiled with pmbootstrap)
    ret = [args.work + "/packages/" + arch + "/APKINDEX.tar.gz"]

    # Upstream postmarketOS binary repository
    urls_todo = []
    for mirror in args.mirrors_postmarketos:
        if mirror:
            urls_todo.append(mirror)

    # Resolve the APKINDEX.$HASH.tar.gz files
    urls_todo += urls(args, False, False)
    for url in urls_todo:
        ret.append(args.work + "/cache_apk_" + arch + "/APKINDEX." +
                   hash(url) + ".tar.gz")

    return ret


def update(args, arch=None, force=False, existing_only=False):
    """
    Download the APKINDEX files for all URLs depending on the architectures.

    :param arch: * one Alpine architecture name ("x86_64", "armhf", ...)
                 * None for all architectures
    :param force: even update when the APKINDEX file is fairly recent
    :param existing_only: only update the APKINDEX files that already exist,
                          this is used by "pmbootstrap update"

    :returns: True when files have been downloaded, False otherwise
    """
    # Skip in offline mode, only show once
    cache_key = "pmb.helpers.repo.update"
    if args.offline:
        if not args.cache[cache_key]["offline_msg_shown"]:
            logging.info("NOTE: skipping package index update (offline mode)")
            args.cache[cache_key]["offline_msg_shown"] = True
        return False

    # Architectures and retention time
    architectures = [arch] if arch else pmb.config.build_device_architectures
    retention_hours = pmb.config.apkindex_retention_time
    retention_seconds = retention_hours * 3600

    # Find outdated APKINDEX files. Formats:
    # outdated: {URL: apkindex_path, ... }
    # outdated_arches: ["armhf", "x86_64", ... ]
    outdated = {}
    outdated_arches = []
    for url in urls(args, False):
        for arch in architectures:
            # APKINDEX file name from the URL
            url_full = url + "/" + arch + "/APKINDEX.tar.gz"
            cache_apk_outside = args.work + "/cache_apk_" + arch
            apkindex = cache_apk_outside + "/APKINDEX." + hash(url) + ".tar.gz"

            # Find update reason, possibly skip non-existing or known 404 files
            reason = None
            if url_full in args.cache[cache_key]["404"]:
                # We already attempted to download this file once in this
                # session
                continue
            elif not os.path.exists(apkindex):
                if existing_only:
                    continue
                reason = "file does not exist yet"
            elif force:
                reason = "forced update"
            elif pmb.helpers.file.is_older_than(apkindex, retention_seconds):
                reason = "older than " + str(retention_hours) + "h"
            if not reason:
                continue

            # Update outdated and outdated_arches
            logging.debug("APKINDEX outdated (" + reason + "): " + url_full)
            outdated[url_full] = apkindex
            if arch not in outdated_arches:
                outdated_arches.append(arch)

    # Bail out or show log message
    if not len(outdated):
        return False
    logging.info("Update package index for " + ", ".join(outdated_arches) +
                 " (" + str(len(outdated)) + " file(s))")

    # Download and move to right location
    for url, target in outdated.items():
        temp = pmb.helpers.http.download(args, url, "APKINDEX", False,
                                         logging.DEBUG, True)
        if not temp:
            args.cache[cache_key]["404"].append(url)
            continue
        target_folder = os.path.dirname(target)
        if not os.path.exists(target_folder):
            pmb.helpers.run.root(args, ["mkdir", "-p", target_folder])
        pmb.helpers.run.root(args, ["cp", temp, target])

    return True


def alpine_apkindex_path(args, repo="main", arch=None):
    """
    Get the path to a specific Alpine APKINDEX file on disk and download it if
    necessary.

    :param repo: Alpine repository name (e.g. "main")
    :param arch: Alpine architecture (e.g. "armhf"), defaults to native arch.
    :returns: full path to the APKINDEX file
    """
    # Repo sanity check
    if repo not in ["main", "community", "testing", "non-free"]:
        raise RuntimeError("Invalid Alpine repository: " + repo)

    # Download the file
    arch = arch or args.arch_native
    update(args, arch)

    # Find it on disk
    repo_link = args.mirror_alpine + args.alpine_version + "/" + repo
    cache_folder = args.work + "/cache_apk_" + arch
    return cache_folder + "/APKINDEX." + hash(repo_link) + ".tar.gz"
