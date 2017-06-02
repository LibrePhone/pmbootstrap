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
import logging
import asyncio
import locale


@asyncio.coroutine
def _execute(loop, args, cmd, log_message, log, return_stdout, check=True):
    logging.debug(log_message)

    class SubprocessProtocol(asyncio.SubprocessProtocol):
        def __init__(self, future):
            self.output = ""
            self.error = ""
            self.return_code = None
            self._future = future

        def pipe_data_received(self, fd, data):
            nonlocal args
            text = data.decode(locale.getpreferredencoding(False))

            if fd == 1:
                # stdout
                if log:
                    args.logfd.write(text)
                else:
                    print(text, end='')
                self.output += text

            elif fd == 2:
                # stderr, possibly do something with color here
                if log:
                    args.logfd.write(text)
                else:
                    print(text, end='')
                self.error += text

            args.logfd.flush()

        def process_exited(self):
            self.return_code = 0
            self._future.set_result(True)

    exit_future = asyncio.Future(loop=loop)
    create = loop.subprocess_exec(lambda: SubprocessProtocol(exit_future), *cmd)
    transport, protocol = yield from create
    yield from exit_future
    transport.close()

    return_code = transport.get_returncode()
    if return_code != 0:
        if check:
            raise RuntimeError("Command failed: \n" + protocol.error)
    args.logfd.write('Program exited with: {}\n'.format(transport.get_returncode()))
    args.logfd.flush()

    if return_stdout:
        return protocol.output
    else:
        return return_code


def core(args, cmd, log_message, log, return_stdout, check=True):
    logging.debug(log_message)
    """
    Run the command and write the output to the log.

    :param check: raise an exception, when the command fails
    :param log: send output to log instead of stdout
    :param return_stdout: return the stdout from the called process
    """
    loop = asyncio.get_event_loop()
    loop.set_debug(False)
    task = _execute(loop, args, cmd, log_message, log, return_stdout, check)
    result = loop.run_until_complete(task)
    return result


def user(args, cmd, log=True, working_dir=None, return_stdout=False,
         check=True):
    """
    :param working_dir: defaults to args.work
    """
    if not working_dir:
        working_dir = args.work

    # TODO: maintain and check against a whitelist
    return core(args, cmd, "% " + " ".join(cmd), log, return_stdout, check)


def root(args, cmd, log=True, working_dir=None, return_stdout=False,
         check=True):
    """
    :param working_dir: defaults to args.work
    """
    cmd = ["sudo"] + cmd
    return user(args, cmd, log, working_dir, return_stdout, check)
