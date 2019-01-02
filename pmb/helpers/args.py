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
import copy
import os
import pmb.config

""" This file constructs the args variable, which is passed to almost all
    functions in the pmbootstrap code base. Here's a listing of the kind of
    information it stores.

    1. Argparse
       Variables directly from command line argument parsing (see
       pmb/parse/arguments.py, the "dest" parameter of the add_argument()
       calls defines where it is stored in args).

       Examples:
       args.action ("zap", "chroot", "build" etc.)
       args.as_root (True when --as-root is passed)
       ...

    2. Argparse merged with others
       Variables from the user's config file (~/.config/pmbootstrap.cfg), that
       can be overridden from the command line (pmb/parse/arguments.py) and
       fall back to the defaults defined in pmb/config/__init__.py (see
       "defaults = {..."). The user's config file gets generated interactively
        with "pmbootstrap init".

       Examples:
       args.aports ("$WORK/cache_git/pmaports", override with --aports)
       args.device ("samsung-i9100", "qemu-amd64" etc.)
       args.work ("/home/user/.local/var/pmbootstrap", override with --work)

    3. Shortcuts
       Long variables or function calls that always return the same information
       may have a shortcut defined, to make the code more readable (see
       add_shortcuts() below).

       Example:
       args.arch_native ("x86_64" etc.)

    4. Cache
       pmbootstrap uses this dictionary to save the result of expensive
       results, so they work a lot faster the next time they are needed in the
       same session. Usually the cache is written to and read from in the same
       Python file, with code similar to the following:

       def lookup(args, key):
           if key in args.cache["mycache"]:
               return args.cache["mycache"][key]
           ret = expensive_operation(args, key)
           args.cache["mycache"][key] = ret
           return ret

       See add_cache() below for details.

    5. Parsed configs
       Similar to the cache above, specific config files get parsed and added
       to args, so they can get accessed quickly (without parsing the configs
       over and over). These configs are not only used in one specific
       location, so having a short name for them increases readability of the
       code as well.

       Examples:
       args.deviceinfo (e.g. {"name": "Mydevice", "arch": "armhf", ...})
       args.pmaports (e.g. {"version": "1", "branch_alpine": "edge", ...})
"""


def fix_mirrors_postmarketos(args):
    """ Fix args.mirrors_postmarketos when it is supposed to be empty or the
        default value.

        In pmb/parse/arguments.py, we set the -mp/--mirror-pmOS argument to
        action="append" and start off with an empty list. That way, users can
        specify multiple custom mirrors by specifying -mp multiple times on the
        command line. Here we fix the default and no mirrors case.

        NOTE: we don't use nargs="+", because it does not play nicely with
        subparsers: <https://bugs.python.org/issue9338> """
    # -mp not specified: use default mirrors
    if not args.mirrors_postmarketos:
        args.mirrors_postmarketos = pmb.config.defaults["mirrors_postmarketos"]

    # -mp="": use no postmarketOS mirrors (build everything locally)
    if args.mirrors_postmarketos == [""]:
        args.mirrors_postmarketos = []


def check_pmaports_path(args):
    """ Make sure that args.aports exists when it was overridden by --aports.
        Without this check, 'pmbootstrap init' would start cloning the
        pmaports into the default folder when args.aports does not exist. """
    if args.from_argparse.aports and not os.path.exists(args.aports):
        raise ValueError("pmaports path (specified with --aports) does"
                         " not exist: " + args.aports)


def replace_placeholders(args):
    """ Replace $WORK and ~ (for path variables) in variables from any config
        (user's config file, default config settings or config parameters
        specified on commandline) """

    # Replace $WORK
    for key, value in pmb.config.defaults.items():
        if key not in args:
            continue
        old = getattr(args, key)
        if isinstance(old, str):
            setattr(args, key, old.replace("$WORK", args.work))

    # Replace ~ (path variables only)
    for key in ["aports", "config", "log", "work"]:
        if key in args:
            setattr(args, key, os.path.expanduser(getattr(args, key)))


def add_shortcuts(args):
    """ Add convenience shortcuts """
    setattr(args, "arch_native", pmb.parse.arch.alpine_native())


def add_cache(args):
    """ Add a caching dict (caches parsing of files etc. for the current
        session) """
    repo_update = {"404": [], "offline_msg_shown": False}
    setattr(args, "cache", {"apkindex": {},
                            "apkbuild": {},
                            "apk_min_version_checked": [],
                            "apk_repository_list_updated": [],
                            "built": {},
                            "find_aport": {},
                            "pmb.helpers.package.depends_recurse": {},
                            "pmb.helpers.package.get": {},
                            "pmb.helpers.repo.update": repo_update})


def add_deviceinfo(args):
    """ Add and verify the deviceinfo (only after initialization) """
    setattr(args, "deviceinfo", pmb.parse.deviceinfo(args))
    arch = args.deviceinfo["arch"]
    if (arch != args.arch_native and
            arch not in pmb.config.build_device_architectures):
        raise ValueError("Arch '" + arch + "' is not available in"
                         " postmarketOS. If you would like to add it, see:"
                         " <https://postmarketos.org/newarch>")


def init(args):
    # Basic initialization
    fix_mirrors_postmarketos(args)
    pmb.config.merge_with_args(args)
    replace_placeholders(args)
    add_shortcuts(args)
    add_cache(args)

    # Initialize logs (we could raise errors below)
    pmb.helpers.logging.init(args)

    # Initialization code which may raise errors
    check_pmaports_path(args)
    if args.action not in ["init", "config", "bootimg_analyze", "log",
                           "shutdown", "zap"]:
        pmb.config.pmaports.read_config_into_args(args)
        add_deviceinfo(args)
    return args


def update_work(args, work):
    """ Update the work path in args.work and wherever $WORK was used. """
    # Start with the unmodified args from argparse
    args_new = copy.deepcopy(args.from_argparse)

    # Keep from the modified args:
    # * the old log file descriptor (so we can close it)
    # * the unmodified args from argparse (to check if --aports was specified)
    args_new.logfd = args.logfd
    args_new.from_argparse = args.from_argparse

    # Generate modified args again, replacing $WORK with the new work folder
    # When args.log is different, this also opens the log in the new location
    args_new.work = work
    args_new = pmb.helpers.args.init(args_new)

    # Overwrite old attributes of args with the new attributes
    for key in vars(args_new):
        setattr(args, key, getattr(args_new, key))
