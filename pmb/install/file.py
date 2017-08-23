"""
Copyright 2017 Pablo Castellano

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

import pmb.config
import pmb.helpers.git


def write_os_release(args, suffix):
    logging.info("(" + suffix + ") write /etc/os-release")
    revision = pmb.helpers.git.rev_parse(args)
    filepath = args.work + "/chroot_" + suffix + "/tmp/os-release"
    os_release = ('PRETTY_NAME="postmarketOS {version}"\n'
                  'NAME="postmarketOS"\n'
                  'VERSION_ID="{version}"\n'
                  'VERSION="{version}-{hash:.8}"\n'
                  'ID="postmarketos"\n'
                  'ID_LIKE="alpine"\n'
                  'HOME_URL="https://www.postmarketos.org/"\n'
                  'SUPPORT_URL="https://github.com/postmarketOS/"\n'
                  'BUG_REPORT_URL="https://github.com/postmarketOS/"\n'
                  'PMOS_HASH="{hash}"\n'
                  ).format(version=pmb.config.version, hash=revision)
    with open(filepath, "w") as handle:
        handle.write(os_release)
    pmb.chroot.root(args, ["mv", "/tmp/os-release", "/etc/os-release"], suffix)
