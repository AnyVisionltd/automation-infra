include ../../Makefile.common

PYTHON_MODULES = $(shell basename $(CURDIR))
export PYTHON_MODULES
PYTHONPATH = ../
export PYTHONPATH

.PHONY: help
help: _help

.PHONY: run
run: _runpyapp ## runs the application

.PHONY: shell
shell: _pipshell ## runs pipenv shell

.PHONY: lint
lint: _lint ## run all linters

.PHONY: test
test: _test-pythonunittest## run only python unit tests

.PHONY: tests
tests: _tests ## run all tests and linters for this repo

.PHONY: test-complexity
test-complexity: _test-complexity ## run only python complexity analysis

.PHONY: test-security
test-security: _test-security ## run only python security analysis

.PHONY: test-lint-python
test-lint-python: _test-lint-python ## run only python linter

.PHONY: test-lint-docker
test-lint-docker: _test-lint-docker ## run only docker linter

.PHONY: test-lint-shellcheck
test-lint-shellcheck: _test-lint-shellcheck ## run only shell/bash linter

.PHONY: clean
clean: ## clean up environment
