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


def replace(path, old, new):
    text = ""
    with open(path, 'r') as handle:
        text = handle.read()

    text = text.replace(old, new)

    with open(path, 'w') as handle:
        handle.write(text)


def is_up_to_date(path_target, path_sources):
    """
    Check if a file is up-to-date by comparing the last modified timestamps
    (just like make does it).

    :param path_target: full path to the target file
    :param path_sources: list of full paths to the source files
    """

    lastmod_source = None
    for path_source in path_sources:
        lastmod = os.path.getmtime(path_source)
        if not lastmod_source or lastmod > lastmod_source:
            lastmod_source = lastmod

    lastmod_target = os.path.getmtime(path_target)

    return lastmod_target >= lastmod_source
