"""
Copyright 2019 Oliver Smith

This file is part of pmbootstrap.

pmbootstrap is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pmbootstrap is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pmbootstrap.  If not, see <http://www.gnu.org/licenses/>.
"""

"""
This file tests all functions from pmb.parse.apkindex.
"""

import collections
import os
import pytest
import sys

# Import from parent directory
sys.path.insert(0, os.path.realpath(
    os.path.join(os.path.dirname(__file__) + "/..")))
import pmb.parse.apkindex
import pmb.helpers.logging
import pmb.helpers.repo


@pytest.fixture
def args(tmpdir, request):
    import pmb.parse
    sys.argv = ["pmbootstrap", "init"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_parse_next_block_exceptions(args):
    # Mapping of input files (inside the /test/testdata/apkindex) to
    # error message substrings
    mapping = {"key_twice": "specified twice",
               "key_missing": "Missing required key",
               "new_line_missing": "does not end with a new line!"}

    # Parse the files
    for file, error_substr in mapping.items():
        path = pmb.config.pmb_src + "/test/testdata/apkindex/" + file
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()

        with pytest.raises(RuntimeError) as e:
            pmb.parse.apkindex.parse_next_block(args, path, lines, [0])
        assert error_substr in str(e.value)


def test_parse_next_block_no_error(args):
    # Read the file
    func = pmb.parse.apkindex.parse_next_block
    path = pmb.config.pmb_src + "/test/testdata/apkindex/no_error"
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()

    # First block
    start = [0]
    block = {'arch': 'x86_64',
             'depends': [],
             'origin': 'musl',
             'pkgname': 'musl',
             'provides': ['so:libc.musl-x86_64.so.1'],
             'timestamp': '1515217616',
             'version': '1.1.18-r5'}
    assert func(args, path, lines, start) == block
    assert start == [24]

    # Second block
    block = {'arch': 'x86_64',
             'depends': ['ca-certificates',
                         'so:libc.musl-x86_64.so.1',
                         'so:libcurl.so.4',
                         'so:libz.so.1'],
             'origin': 'curl',
             'pkgname': 'curl',
             'provides': ['cmd:curl'],
             'timestamp': '1512030418',
             'version': '7.57.0-r0'}
    assert func(args, path, lines, start) == block
    assert start == [45]

    # No more blocks
    assert func(args, path, lines, start) is None
    assert start == [45]


def test_parse_next_block_virtual(args):
    """
    Test parsing a virtual package from an APKINDEX.
    """
    # Read the file
    func = pmb.parse.apkindex.parse_next_block
    path = pmb.config.pmb_src + "/test/testdata/apkindex/virtual_package"
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()

    # First block
    start = [0]
    block = {'arch': 'x86_64',
             'depends': ['so:libc.musl-x86_64.so.1'],
             'origin': 'hello-world',
             'pkgname': 'hello-world',
             'provides': ['cmd:hello-world'],
             'timestamp': '1500000000',
             'version': '2-r0'}
    assert func(args, path, lines, start) == block
    assert start == [20]

    # Second block: virtual package
    block = {'arch': 'noarch',
             'depends': ['hello-world'],
             'pkgname': '.pmbootstrap',
             'provides': [],
             'version': '0'}
    assert func(args, path, lines, start) == block
    assert start == [31]

    # No more blocks
    assert func(args, path, lines, start) is None
    assert start == [31]


def test_parse_add_block(args):
    func = pmb.parse.apkindex.parse_add_block
    multiple_providers = False

    # One package without alias
    ret = {}
    block = {"pkgname": "test", "version": "2"}
    alias = None
    func(ret, block, alias, multiple_providers)
    assert ret == {"test": block}

    # Older packages must not overwrite newer ones
    block_old = {"pkgname": "test", "version": "1"}
    func(ret, block_old, alias, multiple_providers)
    assert ret == {"test": block}

    # Newer packages must overwrite older ones
    block_new = {"pkgname": "test", "version": "3"}
    func(ret, block_new, alias, multiple_providers)
    assert ret == {"test": block_new}

    # Add package with alias
    alias = "test_alias"
    func(ret, block_new, alias, multiple_providers)
    assert ret == {"test": block_new, "test_alias": block_new}


def test_parse_add_block_multiple_providers(args):
    func = pmb.parse.apkindex.parse_add_block

    # One package without alias
    ret = {}
    block = {"pkgname": "test", "version": "2"}
    alias = None
    func(ret, block, alias)
    assert ret == {"test": {"test": block}}

    # Older packages must not overwrite newer ones
    block_old = {"pkgname": "test", "version": "1"}
    func(ret, block_old, alias)
    assert ret == {"test": {"test": block}}

    # Newer packages must overwrite older ones
    block_new = {"pkgname": "test", "version": "3"}
    func(ret, block_new, alias)
    assert ret == {"test": {"test": block_new}}

    # Add package with alias
    alias = "test_alias"
    func(ret, block_new, alias)
    assert ret == {"test": {"test": block_new},
                   "test_alias": {"test": block_new}}

    # Add another package with the same alias
    alias = "test_alias"
    block_test2 = {"pkgname": "test2", "version": "1"}
    func(ret, block_test2, alias)
    assert ret == {"test": {"test": block_new},
                   "test_alias": {"test": block_new, "test2": block_test2}}


def test_parse_invalid_path(args):
    assert pmb.parse.apkindex.parse(args, "/invalid/path/APKINDEX") == {}


def test_parse_cached(args, tmpdir):
    # Create a real file (cache looks at the last modified date)
    path = str(tmpdir) + "/APKINDEX"
    pmb.helpers.run.user(args, ["touch", path])
    lastmod = os.path.getmtime(path)

    # Fill the cache
    args.cache["apkindex"][path] = {
        "lastmod": lastmod,
        "multiple": "cached_result_multiple",
        "single": "cached_result_single",
    }

    # Verify cache usage
    func = pmb.parse.apkindex.parse
    assert func(args, path, True) == "cached_result_multiple"
    assert func(args, path, False) == "cached_result_single"

    # Make cache invalid
    args.cache["apkindex"][path]["lastmod"] -= 10
    assert func(args, path, True) == {}

    # Delete the cache (run twice for both code paths)
    assert pmb.parse.apkindex.clear_cache(args, path) is True
    assert args.cache["apkindex"] == {}
    assert pmb.parse.apkindex.clear_cache(args, path) is False


def test_parse(args):
    path = pmb.config.pmb_src + "/test/testdata/apkindex/no_error"
    block_musl = {'arch': 'x86_64',
                  'depends': [],
                  'origin': 'musl',
                  'pkgname': 'musl',
                  'provides': ['so:libc.musl-x86_64.so.1'],
                  'timestamp': '1515217616',
                  'version': '1.1.18-r5'}
    block_curl = {'arch': 'x86_64',
                  'depends': ['ca-certificates',
                              'so:libc.musl-x86_64.so.1',
                              'so:libcurl.so.4',
                              'so:libz.so.1'],
                  'origin': 'curl',
                  'pkgname': 'curl',
                  'provides': ['cmd:curl'],
                  'timestamp': '1512030418',
                  'version': '7.57.0-r0'}

    # Test without multiple_providers
    ret_single = {'cmd:curl': block_curl,
                  'curl': block_curl,
                  'musl': block_musl,
                  'so:libc.musl-x86_64.so.1': block_musl}
    assert pmb.parse.apkindex.parse(args, path, False) == ret_single
    assert args.cache["apkindex"][path]["single"] == ret_single

    # Test with multiple_providers
    ret_multiple = {'cmd:curl': {"curl": block_curl},
                    'curl': {"curl": block_curl},
                    'musl': {"musl": block_musl},
                    'so:libc.musl-x86_64.so.1': {"musl": block_musl}}
    assert pmb.parse.apkindex.parse(args, path, True) == ret_multiple
    assert args.cache["apkindex"][path]["multiple"] == ret_multiple


def test_parse_virtual(args):
    """
    This APKINDEX contains a virtual package .pbmootstrap. It must not be part
    of the output.
    """
    path = pmb.config.pmb_src + "/test/testdata/apkindex/virtual_package"
    block = {'arch': 'x86_64',
             'depends': ['so:libc.musl-x86_64.so.1'],
             'origin': 'hello-world',
             'pkgname': 'hello-world',
             'provides': ['cmd:hello-world'],
             'timestamp': '1500000000',
             'version': '2-r0'}
    ret = {"hello-world": block, "cmd:hello-world": block}
    assert pmb.parse.apkindex.parse(args, path, False) == ret
    assert args.cache["apkindex"][path]["single"] == ret


def test_providers_invalid_package(args, tmpdir):
    # Create empty APKINDEX
    path = str(tmpdir) + "/APKINDEX"
    pmb.helpers.run.user(args, ["touch", path])

    # Test with must_exist=False
    func = pmb.parse.apkindex.providers
    package = "test"
    indexes = [path]
    assert func(args, package, None, False, indexes) == {}

    # Test with must_exist=True
    with pytest.raises(RuntimeError) as e:
        func(args, package, None, True, indexes)
    assert str(e.value).startswith("Could not find package")


def test_providers_highest_version(args, monkeypatch):
    """
    In this test, we simulate 3 APKINDEX files ("i0", "i1", "i2" instead of
    full paths to real APKINDEX.tar.gz files), and each of them has a different
    version of the same package. The highest version must win, no matter in
    which order the APKINDEX files are processed.
    """
    # Fake parse function
    def return_fake_parse(args, path):
        version_mapping = {"i0": "2", "i1": "3", "i2": "1"}
        package_block = {"pkgname": "test", "version": version_mapping[path]}
        return {"test": {"test": package_block}}
    monkeypatch.setattr(pmb.parse.apkindex, "parse", return_fake_parse)

    # Verify that it picks the highest version
    func = pmb.parse.apkindex.providers
    providers = func(args, "test", indexes=["i0", "i1", "i2"])
    assert providers["test"]["version"] == "3"


def test_package(args, monkeypatch):
    # Override pmb.parse.apkindex.providers()
    providers = collections.OrderedDict()

    def return_providers(*args, **kwargs):
        return providers
    monkeypatch.setattr(pmb.parse.apkindex, "providers", return_providers)

    # Provider with the same pkgname
    func = pmb.parse.apkindex.package
    pkgname = "test"
    providers = {"test2": {"pkgname": "test2"}, "test": {"pkgname": "test"}}
    assert func(args, pkgname) == {"pkgname": "test"}

    # First provider
    providers = {"test2": {"pkgname": "test2"}, "test3": {"pkgname": "test3"}}
    assert func(args, pkgname) == {"pkgname": "test2"}

    # No provider (with must_exist)
    providers = {}
    with pytest.raises(RuntimeError) as e:
        func(args, pkgname)
    assert "not found in any APKINDEX" in str(e.value)

    # No provider (without must_exist)
    assert func(args, pkgname, must_exist=False) is None
