#!/usr/bin/python3
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2023 The Foundation for Public Code <info@publiccode.net>

import unittest
import subprocess
import re

uc = __import__("url-check")


class Test_Context:

	def __init__(self):
		self.now_calls = 0

	def now(self):
		self.now_calls = self.now_calls + 1
		fraction = 100000 + self.now_calls
		return "2023-03-13 14:00:00." + str(fraction)

	# ignore log statements
	def log(self, *args, **kwargs):
		return


class TestSum(unittest.TestCase):

	def test_system_context(self):
		ctx = uc.System_Context()
		when = ctx.now()
		rexp = r"[0-9]{4}-[0-1][0-9]-[0-3][0-9] [0-2][0-9]:[0-5][0-9]:[0-5][0-9]\.[0-9]*"
		x = re.search(rexp, when)
		self.assertEqual(x.string, when)

		# only check that it doesn't crash
		ctx.log("", end="")

	def test_files_from_repo(self):
		repo_name = "blog.publiccode.net"
		repo_url = "https://github.com/publiccodenet/blog.git"

		files = uc.files_from_repo(repo_name, repo_url)
		num_files = len(files)
		self.assertTrue(num_files > 100, f"too few files: {num_files}")

	def test_urls_from(self):
		workdir = "blog.publiccode.net"
		file = "README.md"
		found = uc.urls_from(workdir, file)
		self.assertIn("http://jekyllrb.com/", found)
		self.assertIn("https://bundler.io/", found)
		self.assertIn("https://pages.github.com/", found)

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
		name = "blog.publiccode.net"
		file = "README.md"
		uc.set_used_for_file(checks, name, file)

		self.assertIn("README.md",
				checks["http://jekyllrb.com/"]["used"]["blog.publiccode.net"])
		self.assertIn("README.md",
				checks["https://bundler.io/"]["used"]["blog.publiccode.net"])

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
		repo_name = "blog.publiccode.net"
		repo_url = "https://github.com/publiccodenet/blog.git"
		repos = {repo_name: repo_url}
		repo_files = uc.read_repos_files(repos, Test_Context())
		self.assertIn("README.md", repo_files[repo_name])

	def test_url_check_all(self):

		cmd = "mkdir -pv test-data && echo \
			'One [example link](https://example.org/) in it.\
			 And another [example link](https://example.net/) in it.\
			 And a [bogus link](https://www.bogus.gov/bad) in it.'\
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
				"test-data": []
				}
				}
		}
		checks = uc.url_check_all(checks, repos_files, Test_Context())
		self.maxDiff = None
		self.assertEqual(checks, expected)


if __name__ == "__main__":
	unittest.main()
