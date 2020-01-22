include Makefile.common

.PHONY: help
help: _help

.PHONY: tests
tests: ## run all tests
	@cd ./hwprovisioner && make tests
	@bash ./run_tests.sh

.PHONY: lint
lint: _lint ## run generic linters

.PHONY: test-complexity
test-complexity: _test-complexity ## run only complexity analysis (radon

.PHONY: test-security
test-security: _test-security ## run only security analysis

.PHONY: test-lint-python
test-lint-python: _test-lint-python # run python linters

.PHONY: test-lint-shellcheck
test-lint-shellcheck: _test-lint-shellcheck =# run only shell/bash linter

.PHONY: test-lint-docker
test-lint-docker: _test-lint-docker ## run only docker linter


.PHONY: build-hypervisor
build-hypervisor:
	docker build -f Dockerfile.hypervisor -t hypervisor:latest .
	@echo "Built hypervisor:latest" 
