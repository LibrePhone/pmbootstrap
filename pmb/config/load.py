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
import logging
import configparser
import os
import pmb.config


def load(args):
    cfg = configparser.ConfigParser()
    if os.path.isfile(args.config):
        cfg.read(args.config)

    if "pmbootstrap" not in cfg:
        cfg["pmbootstrap"] = {}

    for key in pmb.config.defaults:
        if key in pmb.config.config_keys and key not in cfg["pmbootstrap"]:
            cfg["pmbootstrap"][key] = str(pmb.config.defaults[key])

        # We used to save default values in the config, which can *not* be
        # configured in "pmbootstrap init". That doesn't make sense, we always
        # want to use the defaults from pmb/config/__init__.py in that case, not
        # some outdated version we saved some time back (eg. aports folder,
        # postmarketOS binary packages mirror).
        if key not in pmb.config.config_keys and key in cfg["pmbootstrap"]:
            logging.debug("Ignored unconfigurable and possibly outdated default"
                          " value from config: " + str(cfg["pmbootstrap"][key]))
            del cfg["pmbootstrap"][key]

    return cfg
