# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2023 The Foundation for Public Code <info@publiccode.net>

# Makefile variables used:
#
# $@ : target label
# $< : the first prerequisite after the colon
# $^ : all of the prerequisite files

BROWSER ?= firefox
SHELL=/bin/bash

.PHONY: default
default: check-all

.PHONY: run
run: url-check.py url-check-run-config.json
	./url-check.py --config=url-check-run-config.json

url-check.test.py: url-check.py

check: url-check.test.py
	./$<
	@echo "SUCCESS $@"

.coverage: url-check.test.py url-check.py
	coverage run url-check.test.py

.PHONY: coverage
coverage: .coverage
	coverage report url-check.py

COVERAGE_PERCENT_CMD=\
`coverage report url-check.py \
 | grep url-check.py \
 | awk '{print $$4}' \
 | sed 's/%//'`

MIN_COVERAGE_PCT_THRESHOLD=100

.PHONY: check-coverage
check-coverage: .coverage
	{ \
		coverage report url-check.py; \
		COVERAGE_PERCENT=$(COVERAGE_PERCENT_CMD); \
		if [ $$COVERAGE_PERCENT -lt $(MIN_COVERAGE_PCT_THRESHOLD) ]; \
		then \
			false; \
		fi \
	}
	@echo "SUCCESS $@"

.PHONY: test
test: run
	if [ $$(grep -c '"failing"' url-check-fails.json) -ne 0 ]; then \
		false; \
	fi
	@echo "SUCCESS $@"

.PHONY: check-all
check-all: check check-coverage test
	@echo "SUCCESS $@"

htmlcov/url-check_py.html: .coverage
	coverage html url-check.py

.PHONY: view-coverage
view-coverage: htmlcov/url-check_py.html
	$(BROWSER) htmlcov/url-check_py.html

.PHONY: tidy
tidy: url-check.py url-check.test.py
	yapf3 --in-place $^

.PHONY: clean
clean:
	rm -vf .coverage

.PHONY: dist-clean
dist-clean:
	git clean -dxff
