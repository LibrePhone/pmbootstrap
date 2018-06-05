#!/bin/bash
#
# This script is meant for the gitlab CI shared runners, not for
# any specific runners. Specific runners are expected to provide
# all of these configurations to save time, at least for now.
# Author: Clayton Craft <clayton@craftyguy.net>

[[ -d "/home/pmos" ]] && echo "pmos user already exists, assume running on pre-configured runner" && exit
mount -t binfmt_misc none /proc/sys/fs/binfmt_misc
apt update
apt install -q -y git sudo shellcheck
pip3 install virtualenv
echo "Creating pmos user"
useradd pmos -m -s /bin/bash -b "/home"
chown -R pmos:pmos .
echo 'pmos ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers
