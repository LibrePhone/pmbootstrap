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
    if postmarketos_mirror and args.mirror_postmarketos:
        if os.path.exists(args.mirror_postmarketos):
            ret.append("/mnt/postmarketos-mirror")
        else:
            ret.append(args.mirror_postmarketos)

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
    mirror = args.mirror_postmarketos
    if mirror:
        if os.path.exists(mirror):
            ret.append(mirror + "/" + arch + "/APKINDEX.tar.gz")
        else:
            # Non-local path: treat it like other URLs
            urls_todo.append(mirror)

    # Resolve the APKINDEX.$HASH.tar.gz files
    urls_todo += urls(args, False, False)
    for url in urls_todo:
        ret.append(args.work + "/cache_apk_" + arch + "/APKINDEX." +
                   hash(url) + ".tar.gz")

    return ret


def update(args, force=False):
    """
    Download the APKINDEX files for all URLs and architectures.
    :arg force: even update when the APKINDEX file is fairly recent
    """

    architectures = pmb.config.build_device_architectures
    retention_hours = pmb.config.apkindex_retention_time
    retention_seconds = retention_hours * 3600

    outdated = {}
    for url in urls(args, False):
        for arch in architectures:
            url_full = url + "/" + arch + "/APKINDEX.tar.gz"
            cache_apk_outside = args.work + "/cache_apk_" + arch
            apkindex = cache_apk_outside + "/APKINDEX." + hash(url) + ".tar.gz"

            reason = None
            if not os.path.exists(apkindex):
                reason = "file does not exist yet"
            elif force:
                reason = "forced update"
            elif pmb.helpers.file.is_older_than(apkindex, retention_seconds):
                reason = "older than " + str(retention_hours) + "h"
            if not reason:
                continue

            logging.debug("APKINDEX outdated (" + reason + "): " + url_full)
            outdated[url_full] = apkindex

    if not len(outdated):
        return

    # Show one message only
    logging.info("Update package index (" + str(len(outdated)) + "x)")
    for url, target in outdated.items():
        # Download and move to right location
        temp = pmb.helpers.http.download(args, url, "APKINDEX", False,
                                         logging.DEBUG)
        target_folder = os.path.dirname(target)
        if not os.path.exists(target_folder):
            pmb.helpers.run.root(args, ["mkdir", "-p", target_folder])
        pmb.helpers.run.root(args, ["cp", temp, target])
