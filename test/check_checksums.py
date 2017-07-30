#!/usr/bin/env python3
import os
import subprocess


def get_changed_files():
    try:
        raw = subprocess.check_output(['git', 'diff', '--name-only', os.environ['TRAVIS_COMMIT_RANGE']])
    except (KeyError, subprocess.CalledProcessError) as e:
        raw = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD~1'])
    return raw.decode().splitlines()


def get_changed_packages():
    files = get_changed_files()
    packages = set()
    for file in files:
        if not file.startswith("aports/"):
            continue
        name = file.split("/")[2]
        packages.add(name)
    return packages


def check_output_always(command):
    try:
        return subprocess.check_output(command)
    except subprocess.CalledProcessError as e:
        return e.output


def check_checksums(package):
    command = ['./pmbootstrap.py', 'checksum', package]
    try:
        subprocess.check_output(command)
    except subprocess.CalledProcessError as e:
        print("Something gone wrong in pmbootstrap. Log:")
        logfile = os.path.expanduser("~/.local/var/pmbootstrap/log.txt")
        with open(logfile) as log:
            print(log.read())

    result = check_output_always(['git', 'status', '--porcelain', '--untracked-files=no']).decode()

    if result == "":
        print("** The checksums are correct")
    else:
        print(result)
        print("** The checksums are not correct")
        exit(1)


if __name__ == "__main__":
    packages = get_changed_packages()

    if len(packages) == 0:
        print("No aports packages changed in this commit")
        exit(0)

    for package in packages:
        print("Checking {} for correct checksums".format(package))
        check_checksums(package)
