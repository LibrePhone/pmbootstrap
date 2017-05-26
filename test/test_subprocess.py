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
import glob


def test_use_pmb_helpers_run_instead_of_subprocess_run():
    src = os.path.abspath(os.path.dirname(__file__) + "/..")
    files = glob.glob(src + "/pmb/**/*.py",
                      recursive=True) + glob.glob(src + "*.py")
    okay = os.path.abspath(src + "/pmb/helpers/run.py")
    for file in files:
        with open(file, "r") as handle:
            source = handle.read()
        if file != okay and "subprocess.run" in source:
            raise RuntimeError("File " + file + " use pmb.helpers.run.user()"
                               " instead of subprocess.run()!")
