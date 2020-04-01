# "heartbeats" service

It is the responsibility of the Heartbeats service to handle heartbeats from
the test infrastructure and update the 'expiration' value assigned to jobs in
redis.

*Scenario: "As a developer, I want to continue using this resource*

## requirements

 - python 3.6.9
 - pipenv (tested on version 2018.11.26)
 - make (tested on version GNU Make 4.1)

## commands

For your convenience, several commands have been added to this directory for you. You can avail of these by running `make <command>`, e.g. `make tests`

```shell
$ make
run                            runs the application
shell                          runs pipenv shell
lint                           run all linters
test                           run only python unit tests
tests                          run all tests and linters for this repo
test-complexity                run only python complexity analysis
test-security                  run only python security analysis
test-lint-python               run only python linter
test-lint-docker               run only docker linter
test-lint-shellcheck           run only shell/bash linter
clean                          clean up environment
```

development
-----------

For convenience it is recommended to use a reload service alongside `make run`. A few options are available. In the dockerfile you will notice we're using 'watchmedo'

## api

```json
# POST /heartbeat/
# description: expose all registered resources
# payload:
# {
#   "allocation_id": "ABCDEF-BASDBASD-121314"
# }
# response:
{
    "status": 200
}
```
