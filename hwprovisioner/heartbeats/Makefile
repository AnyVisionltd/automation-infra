include ../../Makefile.common

PYTHON_MODULES = $(shell basename $(CURDIR))
export PYTHON_MODULES
PYTHON_COVERAGE = webapp
export PYTHON_COVERAGE
PYTHONPATH = $(CURDIR)
export PYTHONPATH

.PHONY: help
help: _help

.PHONY: run
run: build ## runs the application
	@docker run --rm -e REDIS_HOST=${MYIP} -e REDIS_PORT=6379 -e REDIS_DB=0 -e REDIS_USER=guest -e REDIS_PASSWORD=password -v ${PWD}:/src -w /src -p 7080:8080 -ti heartbeats watchmedo auto-restart --recursive -d . -p '*.py' -- python3 -m 'webapp.app' serve

.PHONY: build
build: ## builds the docker image
	@docker build -t=heartbeats .

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
