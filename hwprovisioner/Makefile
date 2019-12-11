MAKEFLAGS += --no-print-directory --silent

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: run
run: ## runs the hardware provisioner (using docker-compose)
	@docker-compose up -d
	@echo 'Open http://localhost:8080/api/v1/doc to get started'

.PHONY: clean
clean: ## cleans up the build artefacts
	@-docker-compose down
	@-docker-compose rm -f
