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
import time
import pmb.helpers.run


def replace(path, old, new):
    text = ""
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()

    text = text.replace(old, new)

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def is_up_to_date(path_sources, path_target=None, lastmod_target=None):
    """
    Check if a file is up-to-date by comparing the last modified timestamps
    (just like make does it).

    :param path_sources: list of full paths to the source files
    :param path_target: full path to the target file
    :param lastmod_target: the timestamp of the target file. specify this as
                           alternative to specifying path_target.
    """

    if path_target and lastmod_target:
        raise RuntimeError(
            "Specify path_target *or* lastmod_target, not both!")

    lastmod_source = None
    for path_source in path_sources:
        lastmod = os.path.getmtime(path_source)
        if not lastmod_source or lastmod > lastmod_source:
            lastmod_source = lastmod

    if path_target:
        lastmod_target = os.path.getmtime(path_target)

    return lastmod_target >= lastmod_source


def is_older_than(path, seconds):
    """
    Check if a single file is older than a given amount of seconds.
    """
    if not os.path.exists(path):
        return True
    lastmod = os.path.getmtime(path)
    return lastmod + seconds < time.time()


def symlink(args, file, link):
    """
    Checks if the symlink is already present, otherwise create it.
    """
    if os.path.exists(link):
        if (os.path.islink(link) and
                os.path.realpath(os.readlink(link)) == os.path.realpath(file)):
            return
        raise RuntimeError("File exists: " + link)
    elif os.path.islink(link):
        os.unlink(link)

    # Create the symlink
    pmb.helpers.run.user(args, ["ln", "-s", file, link])
