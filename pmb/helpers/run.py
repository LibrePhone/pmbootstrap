"""
Copyright 2018 Oliver Smith

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
import shlex
import subprocess
import logging
import os


def core(args, cmd, log_message, log, return_stdout, check=True,
         working_dir=None, background=False):
    """
    Run the command and write the output to the log.

    :param cmd: command as list, e.g. ["echo", "string with spaces"]
    :param log_message: simplified and more readable form of the command, e.g.
                        "(native) % echo test" instead of the full command with
                        entering the chroot and more escaping
    :param log: * True: write stdout and stderr of the running process into
                        the log file (read with "pmbootstrap log").
                * False: redirect stdout and stderr to pmbootstrap stdout
    :param return_stdout: write stdout to a buffer and return it as string when
                          the command is through
    :param check: raise an exception, when the command fails
    :param working_dir: path in host system where the command should run
    :param background: run the process in the background and return the process
                       handler
    :returns: * stdout when return_stdout is True
              * process handler when background is True
              * None otherwise
    """
    logging.debug(log_message)
    logging.verbose("run: " + str(cmd))

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


def flat_cmd(cmd, working_dir=None, env={}):
    """
    Convert a shell command passed as list into a flat shell string with
    proper escaping.

    :param cmd: command as list, e.g. ["echo", "string with spaces"]
    :param working_dir: when set, prepend "cd ...;" to execute the command
                        in the given working directory
    :param env: dict of environment variables to be passed to the command, e.g.
                {"JOBS": "5"}
    :returns: the flat string, e.g.
              echo 'string with spaces'
              cd /home/pmos;echo 'string with spaces'
    """
    # Merge env and cmd into escaped list
    escaped = []
    for key, value in env.items():
        escaped.append(key + "=" + shlex.quote(value))
    for i in range(len(cmd)):
        escaped.append(shlex.quote(cmd[i]))

    # Prepend working dir
    ret = " ".join(escaped)
    if working_dir:
        ret = "cd " + shlex.quote(working_dir) + ";" + ret

    return ret


def user(args, cmd, log=True, working_dir=None, return_stdout=False,
         check=True, background=False, env={}):
    """
    Run a command on the host system as user.

    :param cmd: command as list, e.g. ["echo", "string with spaces"]
    :param log: when set to true, redirect all output to the logfile
    :param working_dir: path in host system where the command should run
    :param return_stdout: write stdout to a buffer and return it as string when
                          the command is through
    :param check: raise an exception, when the command fails
    :param background: run the process in the background and return the process
                       handler
    :param env: dict of environment variables to be passed to the command, e.g.
                {"JOBS": "5"}
    :returns: * stdout when return_stdout is True
              * process handler when background is True
              * None otherwise
    """
    # Readable log message (without all the escaping)
    msg = "% "
    for key, value in env.items():
        msg += key + "=" + value + " "
    if working_dir:
        msg += "cd " + working_dir + "; "
    msg += " ".join(cmd)

    # Add environment variables and run
    if env:
        cmd = ["sh", "-c", flat_cmd(cmd, env=env)]
    return core(args, cmd, msg, log, return_stdout, check, working_dir,
                background)


def root(args, cmd, log=True, working_dir=None, return_stdout=False,
         check=True, background=False, env={}):
    """
    Run a command on the host system as root, with sudo.

    NOTE: See user() above for parameter descriptions.
    """
    if env:
        cmd = ["sh", "-c", flat_cmd(cmd, env=env)]
    cmd = ["sudo"] + cmd
    return user(args, cmd, log, working_dir, return_stdout, check, background)
