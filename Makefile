# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2023 The Foundation for Public Code <info@publiccode.net>

# Makefile variables used:
#
# $@ : target label
# $< : the first prerequisite after the colon
# $^ : all of the prerequisite files

BROWSER ?= firefox
SHELL=/bin/bash

default: check-all

run: url-check.py url-check-repos.json
	./url-check.py

url-check.test.py: url-check.py

check: url-check.test.py
	./$<
	@echo "SUCCESS $@"

.coverage: url-check.test.py
	coverage run url-check.test.py

coverage: .coverage
	coverage report url-check.py

COVERAGE_PERCENT_CMD=\
`coverage report url-check.py \
 | grep url-check.py \
 | awk '{print $$4}' \
 | sed 's/%//'`

COVERAGE_THRESHOLD=100

check-coverage: .coverage
	{ \
		coverage report url-check.py; \
		COVERAGE_PERCENT=$(COVERAGE_PERCENT_CMD); \
		if [ $$COVERAGE_PERCENT -lt $(COVERAGE_THRESHOLD) ]; then \
			false; \
		fi \
	}
	@echo "SUCCESS $@"

check-all: check check-coverage
	@echo "SUCCESS $@"

htmlcov/url-check_py.html: .coverage
	coverage html url-check.py

view-coverage: htmlcov/url-check_py.html
	$(BROWSER) htmlcov/url-check_py.html

tidy: url-check.py url-check.test.py
	yapf3 --in-place $^

clean:
	rm -vf .coverage

dist-clean:
	git clean -dxff
