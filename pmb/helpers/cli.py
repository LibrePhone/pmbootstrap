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
import datetime


def ask(args, question="Continue?", choices=['y', 'n'], default='n',
        lowercase_answer=True):
    date = datetime.datetime.now().strftime("%H:%M:%S")
    question = "[" + date + "] " + question
    if choices:
        question += " (" + str.join("/", choices) + ")"
    if default:
        question += " [" + str(default) + "]"

    ret = input(question + ": ")
    if lowercase_answer:
        ret = ret.lower()
    if ret == "":
        ret = str(default)

    args.logfd.write(question + " " + ret + "\n")
    args.logfd.flush()
    return ret
