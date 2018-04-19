#!/usr/bin/env fish
# Copyright 2018 Oliver Smith
# SPDX-License-Identifier: GPL-3.0-or-later

# Fish compatibility code from envkernel.sh
set script_dir (dirname (status filename))
sh "$script_dir/envkernel.sh" --fish 1>| read -z fishcode

# Verbose output
if [ "$argv" = "-v" ]
	echo "(eval code start)"
	printf "$fishcode"
	echo "(eval code end)"
end

# Execute generated code
echo -e "$fishcode" | source -
