#!/usr/bin/python3
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2023 The Foundation for Public Code <info@publiccode.net>

# defaults
checks_json = "url-check-checks.json"
repos_json = "url-check-repos.json"

import json
import os
import re
import requests
import subprocess
import sys
import datetime


def write_json(json_file, obj):
	with open(json_file, "w") as outfile:
		outfile.write(json.dumps(obj, indent=4) + "\n")


def read_json(json_file):
	if os.path.exists(json_file):
		with open(json_file, "r") as in_file:
			return json.load(in_file)
	return {}


def shell_slurp(cmd_str, working_dir=".", fail_func=None):
	result = subprocess.run(
			cmd_str,
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			cwd=working_dir,
	)
	if (result.returncode and fail_func):
		return fail_func(result)

	return result.stdout.decode("utf-8")


def files_from_repo(repo_dir, repo_url):
	clone_cmd = f"git clone {repo_url} {repo_dir}"
	text = shell_slurp(clone_cmd, ".")

	branch_cmd = "git branch | grep \* | cut -d' ' -f2"
	branch = shell_slurp(branch_cmd, repo_dir).rstrip()

	list_cmd = f"git ls-tree -r --name-only {branch}"
	files = shell_slurp(list_cmd, repo_dir).splitlines()

	return files


def urls_from(workdir, file):
	found = []
	cmd_str = f"grep --extended-regexp --only-matching \
		'(http|https)://[a-zA-Z0-9\./\?=_%:\-]*' \
		'{file}' \
		| sort --unique \
		| grep --invert-match '^http[s]\?://localhost' \
		| grep --invert-match '^http[s]\?://127.0.0.1' \
		| grep --invert-match '^http[s]\?://web.archive.org' \
		"

	urls = shell_slurp(cmd_str, workdir).splitlines()
	for url in urls:
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
	sorted_elems = sorted(stuff.items(), key=lambda el: el[0])
	return {key: val for key, val in sorted_elems}


def status_code_for_url(url):
	try:
		response = requests.head(url, allow_redirects=True, timeout=10)
		return response.status_code
	except Exception:
		return 0


# The System_Context class exists so that tests can intercept system functions.
#
# Rather than always directly call for the current time, tests can inject
# there own values.
#
# Rather than logging directly to the screen, tests can capture the output.
#
class System_Context:

	def now(self):
		return str(datetime.datetime.utcnow())

	def log(self, *args, **kwargs):
		print(*args, **kwargs)


def read_repos_files(repos=read_json(repos_json), ctx=System_Context()):
	repo_files = {}

	for repo_name, repo_url in repos.items():
		ctx.log(repo_name, repo_url)
		files = files_from_repo(repo_name, repo_url)
		repo_files[repo_name] = files

	return repo_files


def url_check_all(
		checks=read_json(checks_json),
		repos_files=read_repos_files(),
		ctx=System_Context()):

	for repo_name, files in repos_files.items():
		clear_previous_used(checks, repo_name)
		set_used(checks, repo_name, files)

	checks = sort_by_key(checks)

	for url, data in checks.items():
		when = ctx.now()
		ctx.log(when, url)
		status_code = status_code_for_url(url)
		ctx.log(status_code, url)
		checks[url]["checks"]["status"] = status_code
		if (status_code == 200):
			checks[url]["checks"].pop("200", None)
			checks[url]["checks"].pop("fail", None)
			checks[url]["checks"]["200"] = when
		else:
			if "fail" in checks[url]["checks"].keys():
				checks[url]["checks"]["fail"]["to"] = when
				checks[url]["checks"]["fail"]["to-code"] = status_code
			else:
				checks[url]["checks"]["fail"] = {}
				checks[url]["checks"]["fail"]["from"] = when
				checks[url]["checks"]["fail"]["from-code"] = status_code

	return checks


def main():  # pragma: no cover
	write_json(checks_json, url_check_all())


if __name__ == "__main__":  # pragma: no cover
	main()
