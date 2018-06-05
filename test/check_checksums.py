#!/usr/bin/env python3
import os
import subprocess
import sys


def get_changed_files():
    try:
        branch = os.environ['CI_COMMIT_REF_NAME']
        raw = subprocess.check_output(['git', 'diff', '--name-only',
                                       'master...{}'.format(branch)])
    except (KeyError, subprocess.CalledProcessError):
            raw = subprocess.check_output(['git', 'diff', '--name-only',
                                           'HEAD~1'])
    return raw.decode().splitlines()


def get_changed_packages():
    files = get_changed_files()
    packages = set()
    for file in files:
        if not file.startswith("aports/"):
            continue
        name = file.split("/")[2]
        package_path = "/".join(file.split("/")[0:3])
        apkbuild_path = os.path.join(package_path, "APKBUILD")
        if not os.path.exists(apkbuild_path):
            print("No APKBUILD found at {}".format(package_path))
            continue
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
        print("Test script failed on checksumming package '{}'".format(package))
        exit(1)

    result = check_output_always(['git', 'status', '--porcelain', '--untracked-files=no']).decode()

    if result == "":
        print("** The checksums are correct")
    else:
        print(result)
        result = check_output_always(['git', 'diff']).decode()
        print(result)
        print("** The checksums are not correct")
        exit(1)


def check_build(packages):
    # Initialize build environment with less logging
    commands = [["build_init"],
                ["--details-to-stdout", "build", "--strict"] + list(packages)]
    for command in commands:
        process = subprocess.Popen(["./pmbootstrap.py"] + command)
        process.communicate()
        if process.returncode != 0:
            print("** Building failed")
            exit(1)


if __name__ == "__main__":
    # Allow to specify "--build" to build instead of only verifying checksums
    build = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "--build":
            build = True
        else:
            print("usage: {} [--build]".format(sys.argv[0]))
            exit(1)

    packages = get_changed_packages()

    if len(packages) == 0:
        print("No aports packages changed in this commit")
        exit(0)

    if build:
        print("Building in strict mode: " + ", ".join(packages))
        check_build(packages)
    else:
        for package in packages:
            print("Checking {} for correct checksums".format(package))
            check_checksums(package)
