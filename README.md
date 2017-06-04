# pmbootstrap
Sophisticated chroot/build/flash tool to develop and install postmarketOS.

[Static code analysis](https://github.com/postmarketOS/pmbootstrap/blob/master/test/static_code_analysis.sh) status: [![travis badge](https://api.travis-ci.org/postmarketOS/pmbootstrap.png?branch=master)](https://travis-ci.org/postmarketOS/pmbootstrap)

## Requirements
* GNU/Linux
* Python 3
* OpenSSL

## Important links
* [postmarketOS introduction](https://ollieparanoid.github.io/post/postmarketOS)
* [Security warning](https://ollieparanoid.github.io/post/security-warning/)
* [Porting progress](https://github.com/postmarketOS/pmbootstrap/wiki/Devices)


## Usage
**Check out the [porting guide](https://github.com/postmarketOS/pmbootstrap/wiki/Porting-to-a-new-device) for a practical start!**

Run `./pmbootstrap.py init` first, to select a target device and the work folder, which will contain all the chroots and other data.
After that, you can run any command. All dependencies (e.g. chroots) will be installed automatically, if they are not available yet.

Here are some examples:


`./pmbootstrap.py --help`:
List all available commands

`./pmbootstrap.py log`:
Run tail -f on the logfile, which contains detailed output. Do this in a second terminal, while executing another `pmbootstrap` command to get all the details.

`./pmbootstrap.py chroot`:
Open a shell inside a native Alpine Linux chroot (~6 MB install size).

`./pmbootstrap.py chroot --suffix=buildroot_armhf`:
Open a shell inside an `armhf` Alpine Linux chroot, with qemu user mode emulation and binfmt support automatically set up.

`./pmbootstrap.py build heimdall`:
Build the "heimdall" package (specify any package from the `aports`-folder here).

`./pmbootstrap.py build heimdall --arch=armhf`:
Build the "heimdall" package for `armhf` inside the `armhf` chroot, with the cross-compiler installed in the native chroot (chroots are connected via distcc).

`./pmbootstrap.py install`:
Generate a system image file with a full postmarketOS installation. All required packages get built first, if they do not exist yet. You will get asked for the "user" password and the root partition password.

`./pmbootstrap.py install --sdcard=/dev/mmcblk0`:
Format and partition the SD card `/dev/mmcblk0`, and put a full postmarketOS installation on it


## Testsuite
Simply install `pytest` (via your package manager or via pip) and run it inside the pmbootstrap folder.


