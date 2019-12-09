MAKEFLAGS += --no-print-directory --silent

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: shell
shell: ## enter virtualenv and install depedencies using pipenv
	@pipenv install --dev
	@pipenv shell

.PHONY: test
test: ## run only unit tests
	@PYTHONPATH=$(CURDIR) pytest

.PHONY: test-complexity
test-complexity: ## run only complexity analysis (radon)
	@radon cc .

.PHONY: test-security
test-security: ## run only security analysis (bandit)
	@bandit -r .

.PHONY: test-lint-python
test-lint-python: ## run only python linter (pylint)
	FAILED=0; \
	pylint infra runner tests || FAILED=1; \
	flake8 . || FAILED=1; \
	[ "$${FAILED}" = "0" ] || exit 1

.PHONY: test-lint-docker
test-lint-docker: ## run only dockerfile linter (hadolint)
	@command -v hadolint > /dev/null || (echo 'hadolint not installed!'; exit 1)
	@find . -type f -name Dockerfile -exec hadolint {} \;

.PHONY: tests
tests: ## run all tests
	FAILED=0; \
	$(MAKE) test-unit || FAILED=1; \
	$(MAKE) test-complexity || FAILED=1; \
	$(MAKE) test-lint-python || FAILED=1; \
	$(MAKE) test-lint-hadolint || FAILED=1; \
	$(MAKE) test-security || FAILED=1; \
	[ "$${FAILED}" = "0" ] || exit 1

.PHONY: build-pipenv
build-pipenv: ## builds the pipenv file, given the requirements3.txt
	@pipenv install -r requirements3.txt
