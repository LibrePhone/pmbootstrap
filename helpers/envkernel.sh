#!/bin/sh
# Copyright 2018 Oliver Smith
# SPDX-License-Identifier: GPL-3.0-or-later
#
# usage example:
# $ cd ~/code/linux
# $ source ~/code/pmbootstrap/helpers/envkernel.sh

check_kernel_folder() {
	[ -e "Kbuild" ] && return
	echo "ERROR: This folder is not a linux source tree: $PWD"
	return 1
}


export_pmbootstrap_dir() {
	# Get pmbootstrap dir based on this script's location
	# See also: <https://stackoverflow.com/a/29835459>
	# shellcheck disable=SC2039
	if [ -n "${BASH_SOURCE[0]}" ]; then
		script_dir="$(dirname "${BASH_SOURCE[0]}")"
	else
		script_dir="$(dirname "$1")"
	fi

	# Fail with debug information
	# shellcheck disable=SC2155
	export pmbootstrap_dir=$(realpath "$script_dir/..")
	if ! [ -e "$pmbootstrap_dir/pmbootstrap.py" ]; then
		echo "ERROR: Failed to get the script's location with your shell."
		echo "Please adjust export_pmbootstrap_dir in envkernel.sh. Debug info:"
		echo "\$1: $1"
		echo "\$pmbootstrap_dir: $pmbootstrap_dir"
		return 1
	fi
}


set_alias_pmbootstrap() {
	pmbootstrap="$pmbootstrap_dir"/pmbootstrap.py
	# shellcheck disable=SC2139
	alias pmbootstrap="$pmbootstrap"
	if [ -e ~/.config/pmbootstrap.cfg ]; then
		$pmbootstrap work_migrate
	else
		echo "NOTE: First run of pmbootstrap, running 'pmbootstrap init'"
		$pmbootstrap init
	fi
}


export_chroot_device_deviceinfo() {
	chroot="$(pmbootstrap config work)/chroot_native"
	device="$(pmbootstrap config device)"
	deviceinfo="$pmbootstrap_dir/aports/device/device-$device/deviceinfo"
	export chroot device deviceinfo
}


check_device() {
	[ -e "$deviceinfo" ] && return
	echo "ERROR: Please select a valid device in 'pmbootstrap init'"
	return 1
}


initialize_chroot() {
	# Don't initialize twice
	flag="$chroot/tmp/envkernel/setup_done"
	[ -e "$flag" ] && return

	# Install needed packages
	echo "Initializing Alpine chroot (details: 'pmbootstrap log')"
	# shellcheck disable=SC2154
	pmbootstrap -q chroot -- apk -q add \
		abuild \
		bc \
		binutils-"$deviceinfo_arch" \
		binutils \
		bison \
		flex \
		gcc-"$deviceinfo_arch" \
		gcc \
		linux-headers \
		libressl-dev \
		make \
		musl-dev \
		ncurses-dev \
		perl || return 1

	# Create /mnt/linux
	sudo mkdir -p "$chroot/mnt/linux"

	# Mark as initialized
	mkdir -p "$chroot/tmp/envkernel"
	touch "$flag"
}


mount_kernel_source() {
	[ -e "$chroot/mnt/linux/Kbuild" ] && return
	sudo mount --bind "$PWD" "$chroot/mnt/linux"
}


create_output_folder() {
	[ -d "$chroot/mnt/linux/.output" ] && return
	mkdir -p ".output"
	pmbootstrap -q chroot -- chown -R pmos:pmos "/mnt/linux/.output"
}


set_alias_make() {
	# Cross compiler prefix
	# shellcheck disable=SC1090
	prefix="$(. "$chroot/usr/share/abuild/functions.sh";
		arch_to_hostspec "$deviceinfo_arch")"

	# Kernel architecture
	case "$deviceinfo_arch" in
		aarch64*) arch="arm64" ;;
		arm*) arch="arm" ;;
	esac

	# Build make command
	cmd="echo '*** pmbootstrap envkernel.sh active for $PWD! ***';"
	cmd="$cmd pmbootstrap -q chroot --"
	cmd="$cmd ARCH=$arch"
	cmd="$cmd CROSS_COMPILE=/usr/bin/$prefix-"
	cmd="$cmd make -C /mnt/linux O=/mnt/linux/.output"
	# shellcheck disable=SC2139
	alias make="$cmd"
}


set_alias_pmbroot_kernelroot() {
	# shellcheck disable=SC2139
	alias pmbroot="cd '$pmbootstrap_dir'"
	# shellcheck disable=SC2139
	alias kernelroot="cd '$PWD'"
}

main() {
	# Stop executing once a function fails
	# shellcheck disable=SC1090
	if check_kernel_folder \
		&& export_pmbootstrap_dir "$1" \
		&& set_alias_pmbootstrap \
		&& export_chroot_device_deviceinfo \
		&& check_device \
		&& . "$deviceinfo" \
		&& initialize_chroot \
		&& mount_kernel_source \
		&& create_output_folder \
		&& set_alias_make \
		&& set_alias_pmbroot_kernelroot; then

		# Success
		echo "pmbootstrap envkernel.sh activated successfully."
		echo " * kernel source:  $PWD"
		echo " * output folder:  $PWD/.output"
		echo " * architecture:   $arch ($device is $deviceinfo_arch)"
		echo " * aliases: make, kernelroot, pmbootstrap, pmbroot" \
			"(see 'type make' etc.)"
	else
		# Failure
		echo "See also: <https://postmarketos.org/troubleshooting>"
		return 1
	fi
}


# Print fish alias syntax (when called from envkernel.fish)
fish_compat() {
	[ "$1" = "--fish" ] || return
	for name in make kernelroot pmbootstrap pmbroot; do
		echo "alias $(alias $name | sed 's/=/ /')"
	done
}

# Run main() with all output redirected to stderr
# Afterwards print fish compatible syntax to stdout
main "$0" >&2 && fish_compat "$1"
