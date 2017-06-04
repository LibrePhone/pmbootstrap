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
import hashlib
import shutil
import logging
import urllib.request
import pmb.helpers.run


def download(args, url, prefix, cache=True):
    """
    Download a file to disk.
    """
    # Create cache folder
    if not os.path.exists(args.work + "/cache_http"):
        pmb.helpers.run.user(args, ["mkdir", "-p", args.work + "/cache_http"])

    # Check if file exists in cache
    prefix = prefix.replace("/", "_")
    path = (args.work + "/cache_http/" + prefix + "_" +
            hashlib.sha256(url.encode("utf-8")).hexdigest())
    if os.path.exists(path):
        if cache:
            return path
        pmb.helpers.run.user(args, ["rm", path])

    # Download the file
    logging.info("Download " + url)
    with urllib.request.urlopen(url) as response:
        with open(path, "wb") as handle:
            shutil.copyfileobj(response, handle)
    return path
