include Makefile.common

RESOURCES_CONFIG_FILE ?= ./example.resources.yml

.PHONY: help
help: _help

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

test-subprocessor:
	./containerize.sh python -m pytest -p pytest_subprocessor automation_infra/tests/plain_tests/ --num-parallel 3

test-ssh-aws:
	./run/aws.sh automation_infra/tests/basic_tests/test_ssh.py

test-infra-aws:
	./run/aws.sh automation_infra/tests/basic_tests/ --num-parallel 3

test-devops-aws:
	./run/aws.sh ../devops-automation-infra/automation/devops_automation_infra/tests/docker_tests/ --sf=\"-p devops_docker_installer -p devops_proxy_container --pdb\" --pdb --num-parallel 3

test-sanity:
	make test-subprocessor
	./run/local.sh automation_infra/tests/basic_tests/test_ssh.py --num-parallel 1
	make test-infra-aws