# pmbootstrap

[**Introduction**](https://postmarketos.org/blog/2017/05/26/intro/) | [**Security Warning**](https://ollieparanoid.github.io/post/security-warning/) | [**Supported Devices**](https://wiki.postmarketos.org/wiki/Supported_devices) | [![travis badge](https://api.travis-ci.org/postmarketOS/pmbootstrap.png?branch=master)](https://travis-ci.org/postmarketOS/pmbootstrap)

Sophisticated chroot/build/flash tool to develop and install postmarketOS.

For in-depth information please refer to the [postmarketOS wiki](https://wiki.postmarketos.org).

## Requirements
* Linux distribution (`x86_64` or `aarch64`)
  * Note: [Windows subsystem for Linux (WSL)](https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux) does **not** work! Please use [VirtualBox](https://www.virtualbox.org/) instead.
* 2 GB of RAM recommended for compiling
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

After a reboot, the device will provide a USB network interface, which we request an IP from, and telnet into to open the full-disk encryption on the main system partition:

```shell
$ dhclient -v enp0s20f0u1
$ telnet 172.16.42.1

Trying 172.16.42.1...
Connected to 172.16.42.1.
Escape character is '^]'.

Enter passphrase for /dev/mapper/mmcblk0p25p2:
Connection closed by foreign host.
```

Once the partition has been unlocked it is possible to connect via SSH:

```shell
$ ssh user@172.16.42.1
```

## Development

### Testing

Install `pytest` (via your package manager or pip) and run it inside the pmbootstrap folder.

## License

[GPLv3](LICENSE)
