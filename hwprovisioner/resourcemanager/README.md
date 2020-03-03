# "resource manager" service

It is the responsibility of the "Resource Manager" service to manage resources that have been provisioned using the Allocate API to a known safe state. The problem to solve here is ensuring that each device is in a clean state, ready for it's next load of tests.

*Scenario: "As a developer, when I no longer have use of a resource, the hw provisioner should ensure that resource has been reset to a known safe configuration so that it's reliable in the next use"*

## commands

For your convenience, several commands have been added to this directory for you. You can avail of these by running `make <command>`, e.g. `make tests`

```shell
$ make
run                            runs the application in docker-compose
tests                          run all modules tests sequentially
shell                          runs pipenv shell
lint                           run all modules linters sequentially
test-complexity                run only python complexity analysis
test-security                  run only python security analysis
test-lint-docker               run only docker linter
test-lint-shellcheck           run only shell/bash linter
clean                          clean up environment
```

## environment variables

`ALLOCATE_API` - where to find the allocate api. default: http://localhost:8080/api
`CONFIG_FILE` - where to find the resources config. default: resources.yml

## config file

This service expects a config file (default: `resources.yml`) which details the
various resources that this service is responsible for. An example of this file
can be found at `./example.resources.yml`.

## api

```json
# The resource manager service has no exposed API. Instead, it gets job from a queue in Redis and communicates directly with the resource
```

