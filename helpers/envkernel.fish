#!/usr/bin/env fish
# Copyright 2018 Oliver Smith
# SPDX-License-Identifier: GPL-3.0-or-later

if [ "$argv" != "" ]
	and [ "$argv" != "--gcc6" ]
	echo "usage: source envkernel.fish"
	echo "optional arguments:"
	echo "    --gcc6        Use GCC6 cross compiler"
	echo "    --help        Show this help message"
	exit 1
end

# Fish compatibility code from envkernel.sh
set script_dir (dirname (status filename))
sh "$script_dir/envkernel.sh" $argv --fish 1>| read -z fishcode

# Verbose output (enable with: 'set ENVKERNEL_FISH_VERBOSE 1')
if [ "$ENVKERNEL_FISH_VERBOSE" = "1" ]
	echo "(eval code start)"
	printf "$fishcode"
	echo "(eval code end)"
end

# Execute generated code
echo -e "$fishcode" | source -
