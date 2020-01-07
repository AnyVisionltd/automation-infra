include ../Makefile.common

MODULES=allocate keepalive resourcemanager

.PHONY: help
help: _help

.PHONY: run
run: ## runs the application in docker-compose
	@docker-compose up

.PHONY: tests
tests: ## run all modules tests sequentially
	@FAILED=0; for dir in $(MODULES); do cd $(CURDIR)/$$dir && make tests || FAILED=1; done; \
	[ "$${FAILED}" = "0" ] || exit 1

.PHONY: shell
shell: _pipshell ## runs pipenv shell

.PHONY: lint
lint: ## run all modules linters sequentially
	@for dir in $(MODULES); do cd $(CURDIR)/$$dir && make lint; done

.PHONY: test-complexity
test-complexity: _test-complexity ## run only python complexity analysis

.PHONY: test-security
test-security: _test-security ## run only python security analysis

.PHONY: test-lint-docker
test-lint-docker: _test-lint-docker ## run only docker linter

.PHONY: test-lint-shellcheck
test-lint-shellcheck: _test-lint-shellcheck ## run only shell/bash linter

.PHONY: clean
clean: ## clean up environment
	@docker-compose rm
