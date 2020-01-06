# agent

It is the responsibility of the agent to inform the Allocate service of the resources the agent is connected to. This populates the inventory on Allocate.

*Scenario: "As a systems engineer, I want to join my nvidia server to the Allocate inventory"*

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

## api

```json
# The agent has no exposed API. Instead it is passed configuration for the resources it is connected to and sends this configuration to the Allocate service. It maintains a connection with the Allocate service which dictates wether the resource it is responsible for should appear "online" or not```
