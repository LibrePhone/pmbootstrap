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
import os


class log_handler(logging.StreamHandler):
    """
    Write to stdout and to the already opened log file.
    """
    _args = None

    def emit(self, record):
        try:
            msg = self.format(record)

            # INFO or higher: Write to stdout
            if not self._args.quiet and record.levelno >= logging.INFO:
                stream = self.stream
                stream.write(msg)
                stream.write(self.terminator)
                self.flush()

            # Everything: Write to logfd
            msg = "(" + str(os.getpid()).zfill(6) + ") " + msg
            self._args.logfd.write(msg + "\n")
            self._args.logfd.flush()

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


def init(args):
    """
    Set log format and add the log file descriptor to args.logfd.
    """
    if not os.path.exists(args.work):
        os.makedirs(args.work)

    date_format = "%H:%M:%S"
    setattr(args, "logfd", open(args.log, "a+"))

    root_logger = logging.getLogger()
    root_logger.handlers = []

    formatter = None
    root_logger.setLevel(logging.DEBUG)
    if args.verbose:
        formatter = logging.Formatter("[%(asctime)s %(module)s]"
                                      " %(message)s", datefmt=date_format)
    else:
        formatter = logging.Formatter("[%(asctime)s] %(message)s",
                                      datefmt=date_format)

    handler = log_handler()
    log_handler._args = args
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    logging.debug('*' * 40)
