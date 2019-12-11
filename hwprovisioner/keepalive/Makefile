MAKEFLAGS += --no-print-directory --silent

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: shell
shell: ## enter virtualenv and install depedencies using pipenv
	@pipenv install --dev
	@pipenv shell

.PHONY: run
run: ## runs the aiohttp server
ifdef KILL_PREVIOUS
	echo 'def'
	-kill $$(ps aux | grep 'webapp.webapp' | grep 'aiohttp.web' | grep -v grep | awk '{ print $$2 }') > /dev/null 2>&1
endif
	@python -m 'aiohttp.web' -H 0.0.0.0 -P 8080 'webapp.webapp:main'

.PHONY: dockerbuild
dockerbuild: ## performs a docker build
	@docker build -t=allocator:local .
