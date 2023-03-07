#!/usr/bin/python3
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2023 The Foundation for Public Code <info@publiccode.net>

import json
import os
import re
import requests
import subprocess
import sys
import datetime

checks_file = "url-check.json";
repos = {
	"standard-for-public-code": "https://github.com/publiccodenet/standard.git",
	"blog.publiccode.net": "https://github.com/publiccodenet/blog.git",
}

if (os.path.exists(checks_file)):
	with open(checks_file, 'r') as in_file:
		urls = json.load(in_file)
else:
	urls = {}

def files_from_repo(name, url):
	clone_cmd = [ "git", "clone", url, name ]
	result = subprocess.run(clone_cmd)

	branch_cmd_str = 'git branch | grep \* | cut -d" " -f2'
	result = subprocess.run(
		branch_cmd_str,
		shell=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		cwd=f"./{name}",
	)
	branch = result.stdout.decode("utf-8").rstrip()
	print("branch: ", branch)

	list_files_cmd = [ "git",  "ls-tree", "-r", "--name-only", branch ]
	result = subprocess.run(
		list_files_cmd,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		cwd=f"./{name}",
	)
	files = result.stdout.decode("utf-8").splitlines()
	return files

def urls_from(name, file):
	found = []
	cmd_strs = [
		# URLs inside parens
		f'grep \'(http[s]\?:\' \'{file}\' | sed -e\'s/.*[(]\(http[s]*:[^)]*\).*/\\1/\'',
		# # URLs inside angle brackets
		f'grep \'<http[s]\?:\' \'{file}\' | sed -e\'s/.*[(]\(http[s]*:[^>]*\).*/\\1/\'',
		# # URLs inside double-quotes
		f'grep \'"http[s]\?:\' \'{file}\' | sed -e\'s/.*[(]\(http[s]*:[^"]*\).*/\\1/\'',
	]
	ignore_urls = '\
		| grep -v \'^http[s]\?://localhost\' \
		| grep -v \'^http[s]\?://127.0.0.1\' \
		| grep -v \'^http[s]\?://web.archive.org\' \
		'
	for cmd_str in cmd_strs:
		result = subprocess.run(
			cmd_str + ignore_urls,
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			cwd=f"./{name}",
		)
		for url in result.stdout.decode("utf-8").splitlines():
			if url.startswith("http"):
				found += [url]
	return found

for name, url in repos.items():
	print(name, url)

	# clear previous pages used for this repo
	for url, data in urls.items():
		if url in urls.keys():
			if name in urls[url]["used"].keys():
				urls[url]["used"][name] = []

	files = files_from_repo(name, url)
	for file in files:
		print("file:", file)
		found =  urls_from(name, file);
		for url in found:
			if url not in urls.keys():
				urls[url] = {}
				urls[url]["checks"] = {}
				urls[url]["used"] = {}
			if name not in urls[url]["used"].keys():
				urls[url]["used"][name] = []
			if file not in urls[url]["used"][name]:
				urls[url]["used"][name] += [file]

# resort the dictionary by url
urls = { key: val for key, val in sorted(urls.items(), key = lambda el: el[0]) }

for url, data in urls.items():
	when = str(datetime.datetime.utcnow())
	print(when, url)
	try:
		status_code = requests.head(url,
			allow_redirects=True,
			timeout=10).status_code
	except Exception:
		status_code = 0
	print(status_code, url)
	urls[url]["checks"][when] = status_code
	# TODO: keep only the last N checks?

with open(checks_file, "w") as outfile:
	outfile.write(json.dumps(urls, indent=4) + "\n")
