#!/usr/bin/python3
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2023 The Foundation for Public Code <info@publiccode.net>

import unittest

import subprocess

uc = __import__("url-check")

class TestSum(unittest.TestCase):
	def test_files_from_repo(self):
		repo_name = "blog.publiccode.net"
		repo_url = "https://github.com/publiccodenet/blog.git"

		# subprocess.run(["rm", "-rf", repo_name])

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
					name2: [
						"_posts/baz.md",
					],
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

		self.assertIn("README.md", checks["http://jekyllrb.com/"]["used"]["blog.publiccode.net"])
		self.assertIn("README.md", checks["https://bundler.io/"]["used"]["blog.publiccode.net"])

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

	def test_read_and_write_checks(self):
		checks_file = "bogus-checks.json"
		subprocess.run(["rm", "-fv", checks_file])
		checks = uc.load_previous_checks(checks_file)
		self.assertEqual({}, checks)
		checks["foo"] = [ "bar", "baz" ]
		checks["baz"] = { "whiz": "bang" }
		uc.write_out_checks(checks_file, checks)
		round_trip = uc.load_previous_checks(checks_file)
		self.assertEqual(round_trip, checks)


if __name__ == "__main__":
	unittest.main()
