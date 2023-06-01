#!/usr/bin/python3
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2023 The Foundation for Public Code <info@publiccode.net>

import datetime
import docopt
import json
import os
import pathlib
import re
import requests
import subprocess
import sys

url_check_version = "0.0.0"

### defaults
default_results_json = "url-check-results.json"
default_config_json = "url-check-config.json"
default_gits_dir = "/tmp/url-check/gits"
default_timeout = "10"

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
        -t SECONDS, --timeout=SECONDS
                                timeout set on the request
                                [default: {default_timeout}]

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
		ctx = default_context()
	ctx.debug(f"working_dir={working_dir}")
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


def urls_from(workdir, file, user_ignore_patterns=[], ctx=None):
	# pull URLs out of the file, including option leading paren
	cmd_str = f"grep --extended-regexp --only-matching --text \
		'[\\(]?(http|https)://[-a-zA-Z0-9\./\\?=_%:\\(\\)]*' \
		'{file}'"

	# remove surrounding parens if they exist
	cmd_str += " | sed -e 's/^(http\\(.*\\))[\\.,]\\?$/http\\1/g'"
	# de-duplicate
	cmd_str += " | sort --unique"

	# print("\n", cmd_str, "\n")

	ignore_patterns = [
			'^http[s]\?://localhost',
			'^http[s]\?://127.0.0.1',
			'^http[s]\?://web.archive.org',
	]
	ignore_patterns.extend(user_ignore_patterns)

	for pattern in ignore_patterns:
		cmd_str += f" | grep --invert-match '{pattern}'"

	lines = shell_slurp(cmd_str, workdir, ctx).splitlines()
	urls = []
	for line in lines:
		# ignore 'binary file matches' messages, only grab URLs
		if line.startswith("http"):
			urls += [line]

	return urls


def clear_previous_used(checks, name):
	# clear previous pages used for this repo
	for url, data in checks.items():
		if name in checks[url]["used"].keys():
			checks[url]["used"][name] = []


def transform_urls(transforms, urls, ctx):
	urls_str = "\n".join(urls)

	cmd = f"echo '{urls_str}'"
	for transform in transforms:
		cmd = cmd + f" | {transform}"

	urls_str = shell_slurp(cmd, ".", ctx)

	transformed_urls = []
	for line in urls_str.splitlines():
		if line.startswith("http"):
			transformed_urls += [line]

	return transformed_urls


def set_used_for_file(
		checks, gits_dir, name, file, ignore_patterns, transforms, ctx):
	repo_dir = os.path.join(gits_dir, name)
	urls = urls_from(repo_dir, file, ignore_patterns, ctx)
	urls = transform_urls(transforms, urls, ctx)
	for url in urls:
		if url not in checks.keys():
			checks[url] = {}
			checks[url]["checks"] = {}
			checks[url]["used"] = {}
		if name not in checks[url]["used"].keys():
			checks[url]["used"][name] = []
		if file not in checks[url]["used"][name]:
			checks[url]["used"][name] += [file]


def set_used(checks, gits_dir, name, files, ignore_patterns, transforms, ctx):
	clear_previous_used(checks, name)
	for file in files:
		set_used_for_file(checks, gits_dir, name, file, ignore_patterns, transforms,
				ctx)


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


def status_code_for_url(url, timeout):
	user_agent = 'url-check github.com/publiccodenet/url-check'
	user_agent += f' v{url_check_version}'
	headers = {
			'User-Agent': user_agent,
	}
	# do we want to set a 'From' header?
	# we could check 'git config --get user.name'
	# and/or 'git config --get user.email' for this.
	# 'From': 'info@examle.org',

	try:
		response = requests.head(
				url, allow_redirects=True, timeout=timeout, headers=headers)
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


global_context = None


def default_context():
	global global_context
	if (global_context == None):
		global_context = System_Context()
	return global_context


def read_repos_files(gits_dir, repos, ctx):
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
		timeout,
		ignore_patterns=[],
		transforms=[],
		ctx=None):

	for url in checks.keys():
		checks[url]["used"] = {}

	for repo_name, files in repos_files.items():
		ctx.log(repo_name, "contains", len(files), "files")
		ctx.debug(files)
		set_used(checks, gits_dir, repo_name, files, ignore_patterns, transforms,
				ctx)

	ctx.debug("checks length:", len(checks), "before unused removed")
	checks = remove_unused(checks)
	ctx.log("performing", len(checks), "checks")

	checks = sort_by_key(checks)

	for url, data in checks.items():
		ctx.log("")
		when = ctx.now()
		ctx.log(when, url)
		status_code = status_code_for_url(url, timeout)
		ctx.log(status_code, url)
		update_status(checks[url]["checks"], status_code, when)

	return checks


def condense_results(checks, repos):
	results = {
			"urls": {},
			"repos": {},
	}

	for repo in repos:
		results["repos"][repo] = "passing"

	for url, check in checks.items():
		if check["checks"]["status"] != 200:
			results["urls"][url] = check
			for repo in check["used"].keys():
				results["repos"][repo] = "failing"

	return results


def write_repo_files(
		repo, repo_checks, repo_condensed, checks_path, check_fails_json):
	report_dir = os.path.dirname(check_fails_json)
	repo_check_base = repo + '-' + os.path.basename(checks_path)
	repo_checks_path = os.path.join(report_dir, repo_check_base)
	write_json(repo_checks_path, repo_checks)

	fails_base = os.path.basename(check_fails_json)
	repo_fails_base = repo + '-' + fails_base
	repo_condensed_path = os.path.join(report_dir, repo_fails_base)
	write_json(repo_condensed_path, repo_condensed)

	look_base = repo + '-url-check-look.json'
	look = pathlib.Path(os.path.join(report_dir, look_base))
	look.unlink(missing_ok=True)
	# default to the full report
	best = repo_checks_path
	# but if failing, link to condensed report
	if (repo_condensed["repos"][repo] == "failing"):
		best = repo_condensed_path
	look.symlink_to(os.path.abspath(best))


def repo_results(repos_info, checks, checks_path, check_fails_json):
	for repo in repos_info.keys():
		repo_checks = {}
		for url, check in checks.items():
			if repo in check["used"].keys():
				repo_checks[url] = check
		repo_condensed = condense_results(repo_checks, [repo])
		write_repo_files(repo, repo_checks, repo_condensed, checks_path,
				check_fails_json)


def main(sys_argv=sys.argv, ctx=default_context()):
	args = docopt.docopt(docopt_str, argv=sys_argv[1:])
	ctx.verbose = args['--verbose']
	ctx.debug(args)
	if args['--version']:
		ctx.log(f"version {url_check_version}")
		return

	gits_dir = args['--gits-dir']
	cfg_path = args['--config']
	checks_path = args['--results']
	timeout = int(args['--timeout'])

	config_obj = read_json(cfg_path)
	repos_info = config_obj["repositories"]
	ignore_patterns_map = config_obj.get("ignore_patterns", {})
	add_ignore_patterns = ignore_patterns_map.keys()
	transforms_map = config_obj.get("transforms", {})
	transforms = transforms_map.keys()

	repos_files = read_repos_files(gits_dir, repos_info, ctx)

	orig_checks = read_json(checks_path)
	checks = url_check_all(gits_dir, orig_checks, repos_files, timeout,
			add_ignore_patterns, transforms, ctx)

	write_json(checks_path, checks)
	condensed = condense_results(checks, repos_info.keys())
	write_json(check_fails_json, condensed)

	repo_results(repos_info, checks, checks_path, check_fails_json)


if __name__ == "__main__":  # pragma: no cover
	main()
