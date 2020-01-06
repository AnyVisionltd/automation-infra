include Makefile.common

.PHONY: help
help: _help

.PHONY: run
run: ## runs the hardware provisioner (using docker-compose)
	@docker-compose up -d
	@echo 'Open http://localhost:8080/api/v1/doc to get started'

.PHONY: clean
clean: ## cleans up the build artefacts
	@-docker-compose down
	@-docker-compose rm -f

.PHONY: tests
tests: ## run all tests
	# ./run_tests.sh
	$(MAKE) _tests

.PHONY: test-complexity
test-complexity: _test-complexity ## run only python complexity analysis

.PHONY: test-security
test-security: _test-security ## run only python security analysis

.PHONY: test-lint-docker
test-lint-docker: _test-lint-docker ## run only docker linter

.PHONY: test-lint-shellcheck
test-lint-shellcheck: _test-lint-shellcheck ## run only shell/bash linter
