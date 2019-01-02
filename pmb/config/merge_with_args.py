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
import pmb.config


def merge_with_args(args):
    """
    We have the internal config (pmb/config/__init__.py) and the user config
    (usually ~/.config/pmbootstrap.cfg, can be changed with the '-c' parameter).

    Args holds the variables parsed from the commandline (e.g. -j fills out
    args.jobs), and values specified on the commandline count the most.

    In case it is not specified on the commandline, for the keys in
    pmb.config.config_keys, we look into the value set in the the user config.

    When that is empty as well (e.g. just before pmbootstrap init), or the key
    is not in pmb.config_keys, we use the default value from the internal
    config.
    """
    # Use defaults from the user's config file
    cfg = pmb.config.load(args)
    for key in cfg["pmbootstrap"]:
        if key not in args or getattr(args, key) is None:
            value = cfg["pmbootstrap"][key]
            if key in pmb.config.defaults:
                default = pmb.config.defaults[key]
                if isinstance(default, bool):
                    value = (value.lower() == "true")
            setattr(args, key, value)

    # Use defaults from pmb.config.defaults
    for key, value in pmb.config.defaults.items():
        if key not in args or getattr(args, key) is None:
            setattr(args, key, value)
