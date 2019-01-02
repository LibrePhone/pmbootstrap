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
import sys

# Import from parent directory
sys.path.insert(0, os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.helpers.mount


def test_umount_all_list(tmpdir):
    # Write fake mounts file
    fake_mounts = str(tmpdir + "/mounts")
    with open(fake_mounts, "w") as handle:
        handle.write("source /test/var/cache\n")
        handle.write("source /test/home/pmos/packages\n")
        handle.write("source /test\n")
        handle.write("source /test/proc\n")
        handle.write("source /test/dev/loop0p2\\040(deleted)\n")

    ret = pmb.helpers.mount.umount_all_list("/no/match", fake_mounts)
    assert ret == []

    ret = pmb.helpers.mount.umount_all_list("/test/var/cache", fake_mounts)
    assert ret == ["/test/var/cache"]

    ret = pmb.helpers.mount.umount_all_list("/test", fake_mounts)
    assert ret == ["/test/var/cache", "/test/proc", "/test/home/pmos/packages",
                   "/test/dev/loop0p2", "/test"]
