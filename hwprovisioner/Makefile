include ../Makefile.common

MODULES=allocate agent keepalive resetresource

.PHONY: help
help: _help

.PHONY: run
run: ## runs the application in docker
	@echo 'TODO ...'

.PHONY: shell
shell: _pipshell ## runs pipenv shell

.PHONY: lint
lint: ## run all modules linters sequentially
	@for dir in $(MODULES); do cd $(CURDIR)/$$dir && pwd && make lint; done

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
