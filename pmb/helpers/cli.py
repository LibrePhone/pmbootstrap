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
import datetime
import logging
import re


def ask(args, question="Continue?", choices=["y", "n"], default="n",
        lowercase_answer=True, validation_regex=None):
    """
    Ask a question on the terminal. When validation_regex is set, the user gets
    asked until the answer matches the regex.
    :returns: the user's answer
    """
    while True:
        date = datetime.datetime.now().strftime("%H:%M:%S")
        question_full = "[" + date + "] " + question
        if choices:
            question_full += " (" + str.join("/", choices) + ")"
        if default:
            question_full += " [" + str(default) + "]"

        ret = input(question_full + ": ")
        if lowercase_answer:
            ret = ret.lower()
        if ret == "":
            ret = str(default)

        args.logfd.write(question_full + " " + ret + "\n")
        args.logfd.flush()

        # Validate with regex
        if not validation_regex:
            return ret

        pattern = re.compile(validation_regex)
        if pattern.match(ret):
            return ret

        logging.fatal("ERROR: Input did not pass validation (regex: " +
                      validation_regex + "). Please try again.")


def confirm(args, question="Continue?", default=False):
    """
    Convenience wrapper around ask for simple yes-no questions with validation.
    :returns: True for "y", False for "n"
    """
    default_str = "y" if default else "n"
    if (args.assume_yes):
        logging.info(question + " (y/n) [" + default_str + "]: y")
        return True
    answer = ask(args, question, ["y", "n"], default_str, True, "(y|n)")
    return answer == "y"
