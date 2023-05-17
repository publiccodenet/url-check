# URL check

<!-- SPDX-License-Identifier: CC0-1.0 -->
<!-- SPDX-FileCopyrightText: 2023 The Foundation for Public Code <info@publiccode.net> -->

The [URL check](url-check.py) is a command-line tool for consolidating the link-checking of multiple repositories into a single batch suitable for running on a schedule.

The output includes reports over-all and per repository of the status of the links contained in the repository files.
Additionally reports are available with full details of each URL checked, as well as a condensed version containing only those URLs which had problems.

The configuration file allows for the exclusion of URLs via regular expression patterns, which has proven essential for reducing noise from sites that have URLs that regularly fail.

## Status: Alpha

The code is [in use](https://publiccodenet.github.io/publiccodenet-url-check/) to regularly check some repositories.
To date, there has been only limited acceptance testing.

## Running the code

The `url-check.py` depends upon the `docopt` python module.
This can be installed via `pip` or your package manager, for instance `python3-docopt` on Debian-like systems.

The [`url-check-config.json`](url-check-config.json) shows an example of how to configure `url-check.py`.

Execute the script via `./url-check.py --config=/path/to/your-config.json`.

See `url-check.py --help` for the list of command-line options.

## Maintenance

The Foundation for Public Code staff is maintaining the code in order facilitate the monitoring of Foundation repositories.

Contributions are welcome, either as issues or code.
If contributing code, please keep contributions focused on a single issue and try to ensure that tests continue to pass.

Please see our [code of conduct](CODE_OF_CONDUCT.md).

## Roadmap

### Near term

* add a second branch with a failing link for the demo
* improve tests
  * corner cases of URLs syntax are under-tested
  * improve confidence in report output

### Longer term

* include URLs that were skipped in the full reports
* allow testing of multiple branches
  * can be done with multiple entries in the config, maybe not needed
* look to see if there is a more git-diff friendly format, json5 ?
  * https://pypi.org/project/json5/
  * Objects and arrays may end with trailing commas
* consider async IO per domain
* make user-agent string configurable

## License

[Licensed](COPYING) under the Creative Commons Zero v1.0 Universal license.
