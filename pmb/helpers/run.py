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
import subprocess
import logging
import os


def core(args, cmd, log_message, log, return_stdout, check=True,
         working_dir=None, background=False):
    logging.debug(log_message)
    """
    Run the command and write the output to the log.

    :param check: raise an exception, when the command fails
    """

    if working_dir:
        working_dir_old = os.getcwd()
        os.chdir(working_dir)

    ret = None

    if background:
        if log:
            ret = subprocess.Popen(cmd, stdout=args.logfd, stderr=args.logfd)
        else:
            ret = subprocess.Popen(cmd)
        logging.debug("Started process in background with PID " + str(ret.pid))
    else:
        try:
            if log:
                if return_stdout:
                    ret = subprocess.check_output(cmd).decode("utf-8")
                    args.logfd.write(ret)
                else:
                    subprocess.check_call(cmd, stdout=args.logfd,
                                          stderr=args.logfd)
                args.logfd.flush()
            else:
                logging.debug("*** output passed to pmbootstrap stdout, not" +
                              " to this log ***")
                subprocess.check_call(cmd)

        except subprocess.CalledProcessError as exc:
            if check:
                if log:
                    logging.debug("^" * 70)
                    logging.info("NOTE: The failed command's output is above"
                                 " the ^^^ line in the logfile: " + args.log)
                raise RuntimeError("Command failed: " + log_message) from exc
            else:
                pass

    if working_dir:
        os.chdir(working_dir_old)
    return ret


def user(args, cmd, log=True, working_dir=None, return_stdout=False,
         check=True, background=False):

    if working_dir:
        msg = "% cd " + working_dir + " && " + " ".join(cmd)
    else:
        msg = "% " + " ".join(cmd)

    # TODO: maintain and check against a whitelist
    return core(args, cmd, msg, log, return_stdout, check, working_dir,
                background)


def root(args, cmd, log=True, working_dir=None, return_stdout=False,
         check=True, background=False):
    """
    :param working_dir: defaults to args.work
    """
    cmd = ["sudo"] + cmd
    return user(args, cmd, log, working_dir, return_stdout, check, background)
