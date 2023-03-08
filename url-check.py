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


def files_from_repo(repo_name, repo_url):
	clone_cmd = ["git", "clone", repo_url, repo_name]
	result = subprocess.run(clone_cmd)

	branch_cmd_str = 'git branch | grep \* | cut -d" " -f2'
	result = subprocess.run(
		branch_cmd_str,
		shell=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		cwd=f"./{repo_name}",
	)
	branch = result.stdout.decode("utf-8").rstrip()

	list_files_cmd = ["git", "ls-tree", "-r", "--name-only", branch]
	result = subprocess.run(
		list_files_cmd,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		cwd=f"./{repo_name}",
	)
	files = result.stdout.decode("utf-8").splitlines()
	return files


def urls_from(workdir, file):
	found = []
	cmd_str = f"grep --extended-regexp --only-matching \
		\"(http|https)://[a-zA-Z0-9./?=_%:\-]*\" \
		\"{file}\" \
		| sort --unique \
		| grep --invert-match '^http[s]\?://localhost' \
		| grep --invert-match '^http[s]\?://127.0.0.1' \
		| grep --invert-match '^http[s]\?://web.archive.org' \
		"
	result = subprocess.run(
		cmd_str,
		shell=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		cwd=workdir,
	)
	for url in result.stdout.decode("utf-8").splitlines():
		# ignore 'binary file matches' messages, only grab URLs
		if url.startswith("http"):
			found += [url]
	return found


def clear_previous_used(checks, name):
	# clear previous pages used for this repo
	for url, data in checks.items():
		if name in checks[url]["used"].keys():
			checks[url]["used"][name] = []


def set_used_for_file(checks, name, file):
	urls = urls_from(name, file)
	for url in urls:
		if url not in checks.keys():
			checks[url] = {}
			checks[url]["checks"] = {}
			checks[url]["used"] = {}
		if name not in checks[url]["used"].keys():
			checks[url]["used"][name] = []
		if file not in checks[url]["used"][name]:
			checks[url]["used"][name] += [file]


def set_used(checks, name, files):
	for file in files:
		set_used_for_file(checks, name, file)


def sort_by_key(stuff):
	return {key: val for key, val in
		sorted(stuff.items(), key=lambda el: el[0])}


def status_code_for_url(url):
	try:
		response = requests.head(url, allow_redirects=True, timeout=10)
		return response.status_code
	except Exception:
		return 0


def write_out_checks(checks_file, checks):
	with open(checks_file, "w") as outfile:
		outfile.write(json.dumps(checks, indent=4) + "\n")


def load_previous_checks(checks_file):
	if os.path.exists(checks_file):
		with open(checks_file, "r") as in_file:
			return json.load(in_file)
	return {}


def url_check_all(checks_file, repos):

	checks = load_previous_checks(checks_file)

	for repo_name, repo_url in repos.items():
		print(repo_name, repo_url)
		clear_previous_used(checks, repo_name)
		files = files_from_repo(repo_name, repo_url)
		set_used(checks, repo_name, files)

	checks = sort_by_key(checks)

	for url, data in checks.items():
		when = str(datetime.datetime.utcnow())
		print(when, url)
		status_code = status_code_for_url(url)
		print(status_code, url)
		checks[url]["checks"][when] = status_code
		# TODO: keep only the last N checks?

	write_out_checks(checks_file, checks)


def main():
	checks_file = "url-check.json"
	repos = {
		"standard-for-public-code": "https://github.com/publiccodenet/standard.git",
		"blog.publiccode.net": "https://github.com/publiccodenet/blog.git",
	}
	url_check_all(checks_file, repos)


if __name__ == "__main__":
	main()
