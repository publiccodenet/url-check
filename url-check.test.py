#!/usr/bin/python3
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2023 The Foundation for Public Code <info@publiccode.net>

import json
import os
import re
import subprocess
import unittest

uc = __import__("url-check")


class Test_Context:

	def __init__(self, capture=False, verbose=False):
		self.now_calls = 0
		self.verbose = verbose
		self.capture = capture
		self.out = ''

	def now(self):
		self.now_calls = self.now_calls + 1
		fraction = 100000 + self.now_calls
		return "2023-03-13 14:00:00." + str(fraction)

	def log(self, *args, **kwargs):
		if (self.capture):
			for arg in args:
				self.out += f" {arg}"
			for key in kwargs:
				self.out += f" {key}: {kwargs[key]}"
			self.out += "\n"
		return

	# ignore debug statements
	def debug(self, *args, **kwargs):
		if self.verbose:
			return self.log(args, kwargs)


class TestSum(unittest.TestCase):

	def test_system_context(self):
		ctx = uc.System_Context()
		when = ctx.now()
		rexp = r"[0-9]{4}-[0-1][0-9]-[0-3][0-9] [0-2][0-9]:[0-5][0-9]:[0-5][0-9]\.[0-9]*"
		x = re.search(rexp, when)
		self.assertEqual(x.string, when)

		ctx.debug("THIS SHOULD NOT BE SEEN", end="")
		# only check that it doesn't crash
		ctx.log("", end="")
		ctx.verbose = True
		ctx.debug("", end="")

	def test_files_from_repo(self):
		repos_dir = '/tmp/url-check-tests/gits'
		repo_name = "url-check"
		repo_url = "https://github.com/publiccodenet/url-check.git"
		branch = "main"

		files = uc.files_from_repo(repos_dir, repo_name, repo_url, branch)
		num_files = len(files)
		self.assertGreater(num_files, 5, f"too few files: {num_files}")

	def test_urls_from(self):
		repos_dir = '/tmp/url-check-tests/gits'
		name = "url-check"
		workdir = os.path.join(repos_dir, name)
		file = "url-check.test.py"
		found = uc.urls_from(workdir, file)
		self.assertIn("https://example.org/", found)
		self.assertIn("http://bogus.gov", found)

	def test_clear_previous_used(self):
		name1 = "blog.example.net"
		name2 = "blog.example.eu"
		all_checks = {
				"http://example.org": {
				"checks": {
				"2023-03-07 13:53:33.874496": 200,
				"2023-03-08 14:10:52.185373": 200,
				},
				"used": {
				name1: [
				"_posts/foo.md",
				"_posts/bar.md",
				],
				name2: ["_posts/baz.md",],
				},
				},
		}

		uc.clear_previous_used(all_checks, name1)

		name1used = all_checks["http://example.org"]["used"][name1]
		self.assertEqual(name1used, [])

		name2used = all_checks["http://example.org"]["used"][name2]
		self.assertEqual(name2used, ["_posts/baz.md"])

	def test_set_used(self):
		checks = {}
		repos_dir = "/tmp/url-check-tests/gits"
		name = "url-check"
		file = "url-check.test.py"
		uc.set_used_for_file(checks, repos_dir, name, file)

		# print('checks: ', json.dumps(checks, indent=4) + "\n")

		self.assertIn(file, checks["https://example.org/"]["used"][name])
		self.assertIn(file, checks["http://bogus.gov"]["used"][name])

	def test_sort_by_key(self):
		stuff = {
				"a": "foo",
				"c": "baz",
				"b": "bar",
		}
		stuff = uc.sort_by_key(stuff)
		keys = ""
		for key, val in stuff.items():
			keys += key
		self.assertEqual("abc", keys)

	def test_status_code_for_url(self):
		status_code = uc.status_code_for_url("http://example.org")
		self.assertEqual(status_code, 200)

	def test_status_code_for_bad_url(self):
		status_code = uc.status_code_for_url("http://bogus.gov")
		self.assertEqual(status_code, 0)

	def test_read_and_write_json(self):
		json_file = "test-obj.json"
		subprocess.run(["rm", "-f", json_file])
		obj = uc.read_json(json_file)
		self.assertEqual({}, obj)
		obj["foo"] = ["bar", "baz"]
		obj["baz"] = {"whiz": "bang"}
		uc.write_json(json_file, obj)
		round_trip = uc.read_json(json_file)
		self.assertEqual(round_trip, obj)
		subprocess.run(["rm", "-f", json_file])

	def test_shell_slurp(self):
		cmd = "echo 'foo'; echo 'bar'"
		stuff = uc.shell_slurp(cmd).splitlines()
		expected = ["foo", "bar"]
		self.assertEqual(stuff, expected)

	def test_shell_slurp(self):
		context = {}

		def fail_handler(result):
			context["err"] = result.returncode
			return "BANG: " + str(result.returncode)

		cmd = "echo 'whiz' && exit 42"
		stuff = uc.shell_slurp(cmd, fail_func=fail_handler)
		self.assertEqual(stuff, "BANG: 42")
		self.assertEqual(context["err"], 42)

	def test_read_repos_files(self):
		repo_name = "url-check"
		repo_url = "https://github.com/publiccodenet/url-check.git"
		repos = {repo_name: {"url": repo_url, "branch": "main"}}
		repos_dir = '/tmp/url-check-tests/gits'
		repo_files = uc.read_repos_files(repos_dir, repos, Test_Context())
		self.assertIn("url-check.test.py", repo_files[repo_name])

	def test_remove_unused(self):
		url3 = "https://example.org/three.html"
		checks = {
				"https://example.org/one.html": {
				"checks": {
				"status": 200,
				"200": "2023-05-04 08:55:37.504684"
				},
				"used": {
				"foo": ["posts/stuff.html"]
				}
				},
				"https://example.org/obsolete.html": {
				"checks": {
				"status": 200,
				"200": "2023-05-04 08:55:37.694390"
				},
				"used": {
				"foo": []
				}
				},
				url3: {
				"checks": {
				"status": 200,
				"200": "2023-05-04 08:55:37.846483"
				},
				"used": {
				"foo": ["posts/more-stuff.html"],
				"bar": []
				}
				},
		}
		checks = uc.remove_unused(checks)
		urls = checks.keys()
		self.assertIn("https://example.org/one.html", urls)
		self.assertNotIn("https://example.org/obsolete.html", urls)
		self.assertIn("https://example.org/three.html", urls)
		self.assertEqual(len(checks[url3]["used"].keys()), 1)

	def test_url_check_all(self):
		cmd = "mkdir -pv test-data && echo \
			'One [example link](https://example.org/) in it.\
			 And another [example link](https://example.net/) in it.\
			 And a [bogus link](https://www.bogus.gov/bad) in it.\
			 And another [bogus link](https://www.bogus.gov/bad2) in it.'\
			> test-data/foo.md"

		uc.shell_slurp(cmd)
		repos_files = {"test-data": ["foo.md"]}

		checks = {
				"https://example.net/": {
				"checks": {
				"status": 404,
				"fail": {
				"from": "2023-03-01 12:22:00.000000",
				"from-code": 404,
				"to": "2023-03-08 15:25:03.345678",
				"to-code": 404
				}
				},
				"used": {
				"test-data": ["foo.md"]
				}
				},
				"https://www.bogus.gov/bad": {
				"checks": {
				"status": 404,
				"fail": {
				"from": "2023-03-02 15:25:00.123456",
				"from-code": 404
				}
				},
				"used": {
				"test-data": ["foo.md"]
				}
				},
				"https://www.bogus.gov/bad2": {
				"checks": {
				"status": 200,
				"200": "2023-03-08 15:25:04.456789",
				},
				"used": {
				"test-data": ["foo.md"]
				}
				}
		}

		expected = {
				"https://example.net/": {
				"checks": {
				"status": 200,
				"200": "2023-03-13 14:00:00.100001"
				},
				"used": {
				"test-data": ["foo.md"]
				}
				},
				"https://example.org/": {
				"checks": {
				"status": 200,
				"200": "2023-03-13 14:00:00.100002"
				},
				"used": {
				"test-data": ["foo.md"]
				}
				},
				"https://www.bogus.gov/bad": {
				"checks": {
				"status": 0,
				"fail": {
				"from": "2023-03-02 15:25:00.123456",
				"from-code": 404,
				"to": "2023-03-13 14:00:00.100003",
				"to-code": 0
				}
				},
				"used": {
				"test-data": ["foo.md"]
				}
				},
				"https://www.bogus.gov/bad2": {
				"checks": {
				"status": 0,
				"200": "2023-03-08 15:25:04.456789",
				"fail": {
				"from": "2023-03-13 14:00:00.100004",
				"from-code": 0
				}
				},
				"used": {
				"test-data": ["foo.md"]
				}
				}
		}
		checks = uc.url_check_all('.', checks, repos_files, Test_Context())
		self.maxDiff = None
		self.assertEqual(checks, expected)

		expected.pop("https://example.net/")
		expected.pop("https://example.org/")
		fails = uc.extract_fails(checks)
		self.assertEqual(fails, expected)

	def test_main_version(self):
		argv = ['url-check', '--version']
		ctx = Test_Context(capture=True)
		uc.main(argv, ctx)
		self.assertIn(uc.url_check_version, ctx.out)

	def test_main(self):
		repos_dir = '/tmp/url-check-tests/gits'
		repos_cfg = os.path.join(repos_dir, 'test-repos.json')
		uc.write_json(
				repos_cfg, {
				"url-check": {
				"url": "https://github.com/publiccodenet/url-check.git",
				"branch": "main"
				}
				})
		checks_json = os.path.join(repos_dir, 'test-repos-checks.json')
		uc.write_json(checks_json, {})

		argv = [
				'url-check',
				'--verbose',
				f'--gits-dir={repos_dir}',
				f'--repos={repos_cfg}',
				f'--checks={checks_json}',
		]
		ctx = Test_Context()
		uc.main(argv, ctx)
		checks = uc.read_json(checks_json)
		check = checks["https://example.org/"]
		self.assertEqual(200, check["checks"]["status"])
		check = checks["https://example.org/one.html"]
		self.assertEqual(404, check["checks"]["status"])


if __name__ == "__main__":
	unittest.main()
