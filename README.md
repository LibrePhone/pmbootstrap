# pmbootstrap

[**Introduction**](https://postmarketos.org/blog/2017/05/26/intro/) | [**Security Warning**](https://ollieparanoid.github.io/post/security-warning/) | [**Supported Devices**](https://wiki.postmarketos.org/wiki/Supported_devices) | [![travis badge](https://api.travis-ci.org/postmarketOS/pmbootstrap.png?branch=master)](https://travis-ci.org/postmarketOS/pmbootstrap) | [![Coverage status](https://coveralls.io/repos/github/postmarketOS/pmbootstrap/badge.svg)](https://coveralls.io/github/postmarketOS)

Sophisticated chroot/build/flash tool to develop and install postmarketOS.

For in-depth information please refer to the [postmarketOS wiki](https://wiki.postmarketos.org).

## Requirements
* 2 GB of RAM recommended for compiling
* Linux distribution (`x86_64` or `aarch64`)
  * [Windows subsystem for Linux (WSL)](https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux) does **not** work! Please use [VirtualBox](https://www.virtualbox.org/) instead.
  * Kernels based on the grsec patchset [do **not** work](https://github.com/postmarketOS/pmbootstrap/issues/107) *(Alpine: use linux-vanilla instead of linux-hardened, Arch: linux-hardened [is not based on grsec](https://www.reddit.com/r/archlinux/comments/68b2jn/linuxhardened_in_community_repo_a_grsecurity/))*
* Python 3.4+
* OpenSSL

## Usage

Assuming you have a supported device, you can build and flash a postmarketOS image by running through the following steps. For new devices check the [porting guide](https://wiki.postmarketos.org/wiki/Porting_to_a_new_device).

First, clone the git repository and initialize your pmbootstrap environment:

```shell
$ git clone https://github.com/postmarketOS/pmbootstrap
$ cd pmbootstrap
$ ./pmbootstrap.py init
```

While running any pmbootstrap command, it's always useful to have a log open in a separate window where further details can be seen:

```shell
$ ./pmbootstrap.py log
```

It's now time to run a full build which will create the boot and system images:

```shell
$ ./pmbootstrap.py install
```

Once your device is connected and is ready to be flashed (e.g. via fastboot), you can run a flash of the kernel (boot) and system partitions:

```shell
$ ./pmbootstrap.py flasher flash_kernel
$ ./pmbootstrap.py flasher flash_system
```

After a reboot, the device will prompt for the full-disk encryption password, which you typed in the install step (unless you have disabled full-disk encryption with `--no-fde`). Once the partition has been unlocked it is possible to connect via SSH:

```shell
$ dhclient -v enp0s20f0u1
$ ssh user@172.16.42.1
```

## Development

### Testing

Install `pytest` (via your package manager or pip) and run it inside the pmbootstrap folder.

## License

[GPLv3](LICENSE)
