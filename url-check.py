#!/usr/bin/python3
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2023 The Foundation for Public Code <info@publiccode.net>

import datetime
import docopt
import json
import os
import re
import requests
import subprocess
import sys

url_check_version = "0.0.0"

### defaults
default_results_json = "url-check-results.json"
default_config_json = "url-check-config.json"
default_gits_dir = "/tmp/url-check/gits"

check_fails_json = "url-check-fails.json"

docopt_str = f"""
{sys.argv[0]}: Checker for URLs found in git repositories

Usage:
        {sys.argv[0]} [options]

Options:
        -g DIR, --gits-dir=DIR  directory in to which to clone repositories
                                [default: {default_gits_dir}]
        -c PATH, --config=PATH  path to the config JSON file,
                                [default: {default_config_json}]
        -r PATH, --results=PATH path to the JSON check results file, if the
                                file already exists, it will be modified
                                [default: {default_results_json}]

        -h, --help              Prints this message
        -V, --version           Prints the version ({url_check_version})
        -v, --verbose           Debug output

DETAILS:

The format of the {default_config_json} is ...

The format of the {default_results_json} is ...

"""


def write_json(json_file, obj):
	with open(json_file, "w") as outfile:
		outfile.write(json.dumps(obj, indent=4) + "\n")


def read_json(json_file):
	if not os.path.exists(json_file):
		return {}
	with open(json_file, "r") as in_file:
		return json.load(in_file)


# spawn a shell to run the commmand(s),
# returns the text which would have been output to the screen
def shell_slurp(cmd_str, working_dir=os.getcwd(), ctx=None, fail_func=None):
	if ctx == None:
		ctx = System_Context()
	ctx.debug(f"working_dir=${working_dir}")
	ctx.debug(cmd_str)
	result = subprocess.run(
			cmd_str,
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			cwd=working_dir,
	)
	ctx.debug(f"return code: {result.returncode}")
	if (result.returncode and fail_func):
		return fail_func(result)

	text = result.stdout.decode("utf-8")
	ctx.debug(text)
	return text


def files_from_repo(repos_basedir, repo_name, repo_url, branch, ctx=None):

	cmd = f"mkdir -pv {repos_basedir}"
	shell_slurp(cmd, os.getcwd(), ctx)

	cmd = f"git clone {repo_url} {repo_name}"
	shell_slurp(cmd, repos_basedir, ctx)
	repo_dir = os.path.join(repos_basedir, repo_name)

	cmd = f"git switch {branch}"
	shell_slurp(cmd, repo_dir, ctx)

	cmd = f"git fetch --all"
	shell_slurp(cmd, repo_dir, ctx)

	cmd = f"git reset --hard origin/{branch}"
	shell_slurp(cmd, repo_dir, ctx)

	cmd = f"git ls-tree -r --name-only {branch}"
	files = shell_slurp(cmd, repo_dir, ctx).splitlines()

	return files


def urls_from(workdir, file, user_ignore_patterns=[]):
	found = []
	cmd_str = f"grep --extended-regexp --only-matching \
		'(http|https)://[a-zA-Z0-9\./\?=_%:\-]*' \
		'{file}' \
		| sort --unique"

	ignore_patterns = [
			'^http[s]\?://localhost',
			'^http[s]\?://127.0.0.1',
			'^http[s]\?://web.archive.org',
	]
	ignore_patterns.extend(user_ignore_patterns)

	for pattern in ignore_patterns:
		cmd_str += f" | grep --invert-match '{pattern}'"

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


def set_used_for_file(checks, gits_dir, name, file, ignore_patterns):
	repo_dir = os.path.join(gits_dir, name)
	urls = urls_from(repo_dir, file, ignore_patterns)
	for url in urls:
		if url not in checks.keys():
			checks[url] = {}
			checks[url]["checks"] = {}
			checks[url]["used"] = {}
		if name not in checks[url]["used"].keys():
			checks[url]["used"][name] = []
		if file not in checks[url]["used"][name]:
			checks[url]["used"][name] += [file]


def set_used(checks, gits_dir, name, files, ignore_patterns):
	clear_previous_used(checks, name)
	for file in files:
		set_used_for_file(checks, gits_dir, name, file, ignore_patterns)


def remove_unused(checks):
	unused = []
	for url in checks.keys():
		used = {}
		for name in checks[url]["used"]:
			if len(checks[url]["used"][name]) > 0:
				used[name] = True
			else:
				used[name] = False

		used_at_all = False
		for name in used.keys():
			if (used[name]):
				used_at_all = True
			else:
				checks[url]["used"].pop(name, None)

		if not (used_at_all):
			unused.append(url)

	for url in unused:
		checks.pop(url, None)

	return checks


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

	verbose = False

	def now(self):
		return str(datetime.datetime.utcnow())

	def log(self, *args, **kwargs):
		print(*args, **kwargs)

	def debug(self, *args, **kwargs):
		if (self.verbose):
			print(*args, **kwargs)


def read_repos_files(gits_dir, repos, ctx=System_Context()):
	repo_files = {}

	for repo_name, repo_data in repos.items():
		repo_url = repo_data.get("url")
		branch = repo_data.get("branch")
		ctx.log(repo_name, repo_url, branch)
		files = files_from_repo(gits_dir, repo_name, repo_url, branch, ctx)
		repo_files[repo_name] = files

	return repo_files


# if we got a 200, then everything is fine again, forget the fails
# else if it the first fail, set the "fail" "from"
# otherwise, the values in "fail" "to"
def update_status(check, status_code, when):
	check["status"] = status_code
	if (status_code == 200):
		check.pop("200", None)
		check.pop("fail", None)
		check["200"] = when
		return

	if "fail" not in check.keys():
		check["fail"] = {}
		check["fail"]["from"] = when
		check["fail"]["from-code"] = status_code
	else:
		check["fail"]["to"] = when
		check["fail"]["to-code"] = status_code


def url_check_all(gits_dir,
		checks,
		repos_files,
		ignore_patterns=[],
		ctx=System_Context()):

	for repo_name, files in repos_files.items():
		set_used(checks, gits_dir, repo_name, files, ignore_patterns)

	checks = remove_unused(checks)

	checks = sort_by_key(checks)

	for url, data in checks.items():
		when = ctx.now()
		ctx.log(when, url)
		status_code = status_code_for_url(url)
		ctx.log(status_code, url)
		update_status(checks[url]["checks"], status_code, when)
		ctx.log("")

	return checks


def extract_fails(checks):
	fails = {}
	for url, check in checks.items():
		if check["checks"]["status"] != 200:
			fails[url] = check
	return fails


def main(sys_argv=sys.argv, ctx=System_Context()):
	args = docopt.docopt(docopt_str, argv=sys_argv[1:])
	ctx.verbose = args['--verbose']
	ctx.debug(args)
	if args['--version']:
		ctx.log(f"version {url_check_version}")
		return

	gits_dir = args['--gits-dir']
	cfg_path = args['--config']
	checks_path = args['--results']

	config_obj = read_json(cfg_path)
	repos_info = config_obj["repositories"]
	add_ignore_patterns = config_obj.get("ignore_patterns", [])

	repos_files = read_repos_files(gits_dir, repos_info, ctx)

	orig_checks = read_json(checks_path)
	checks = url_check_all(gits_dir, orig_checks, repos_files,
			add_ignore_patterns, ctx)

	write_json(checks_path, checks)
	write_json(check_fails_json, extract_fails(checks))


if __name__ == "__main__":  # pragma: no cover
	main()
