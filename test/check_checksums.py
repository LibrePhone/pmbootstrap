#!/usr/bin/env python3
import os
import subprocess
import sys


def get_changed_files():
    try:
        raw = subprocess.check_output(['git', 'diff', '--name-only', os.environ['TRAVIS_COMMIT_RANGE']])
    except (KeyError, subprocess.CalledProcessError) as e:
        if 'TRAVIS_PULL_REQUEST' in os.environ and os.environ['TRAVIS_PULL_REQUEST'] == "true":
            branch = os.environ['TRAVIS_PULL_REQUEST_BRANCH']
            raw = subprocess.check_output(['git', 'diff', '--name-only', 'master...{}'.format(branch)])
        else:
            raw = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD~1'])
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
    command = (["./pmbootstrap.py", "--details-to-stdout", "build",
                "--strict"] + list(packages))
    try:
        process = subprocess.Popen(command)
        process.communicate()
    except subprocess.CalledProcessError as e:
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

    if 'TRAVIS_COMMIT_RANGE' in os.environ:
        print('Checking commit range: {}'.format(os.environ['TRAVIS_COMMIT_RANGE']))
    if 'TRAVIS_PULL_REQUEST_BRANCH' in os.environ:
        print('Checking PR branch: {}'.format(os.environ['TRAVIS_PULL_REQUEST_BRANCH']))

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
