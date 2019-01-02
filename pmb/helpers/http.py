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
import hashlib
import shutil
import logging
import urllib.request
import pmb.helpers.run


def download(args, url, prefix, cache=True, loglevel=logging.INFO,
             allow_404=False):
    """ Download a file to disk.

        :param url: the http(s) address of to the file to download
        :param prefix: for the cache, to make it easier to find (cache files
                       get a hash of the URL after the prefix)
        :param loglevel: change to logging.DEBUG to only display the download
                         message in 'pmbootstrap log', not in stdout. We use
                         this when downloading many APKINDEX files at once, no
                         point in showing a dozen messages.
        :param allow_404: do not raise an exception when the server responds
                          with a 404 Not Found error. Only display a warning on
                          stdout (no matter if loglevel is changed).
        :returns: path to the downloaded file in the cache or None on 404 """
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
    logging.log(loglevel, "Download " + url)
    try:
        with urllib.request.urlopen(url) as response:
            with open(path, "wb") as handle:
                shutil.copyfileobj(response, handle)
    # Handle 404
    except urllib.error.HTTPError as e:
        if e.code == 404 and allow_404:
            logging.warning("WARNING: file not found: " + url)
            return None
        raise

    # Return path in cache
    return path
