# "allocate" service

It is the responsibility of the Allocate service to "allocate" compute resources to users.

*Scenario: "As a developer, I want a dedicated nvidia GeForce RTX 208 to develop and test against"*

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

For convenience it is recommended to use a reload service alongside `make run`. A few options are available. In the following example we'll just use a python3 script [https://gist.github.com/pemcconnell-anyvision/197b26fcb08c985f0a2001f234793cf2](https://gist.github.com/pemcconnell-anyvision/197b26fcb08c985f0a2001f234793cf2)

```sh
autoreload.py KILL_PREVIOUS=1 make run

# visit http://localhost:8080/
```

Here `autoreload` will rerun the command when it detects a change to the
file-system. `KILL_PREVIOUS=1` will attempt to kill any previous running
instances (required due to the app reserving a port on the host). Finally
`make run` will run the app on :8080.

## api

```json
# GET /inventory/
# description: expose all registered resources
# response:
{
    "status": 200,
    "data": [
        {
            "inventory_id": "8a526e72-bcde-45e6-8a5f-f598b350f093",
            "labels": ["nvidia"],
            "cpu_count": 12,
            "memory_gb": 32,
            "gpu": [{
                "label": "GeForce RTX 208",
                "memory_gb": 2,
            }],
            "type": "server-onsite",
        },
        {
            "inventory_id": "2a526e72-bcde-45e6-8a5f-f598b350f091",
            "labels": ["intel-nuc"],
            "cpu_count": 8,
            "memory_gb": 16,
            "gpu": [{
                "label": "Radeon RX 540",
                "memory_gb": 1,
            }],
            "type": "device",
        },
    ]
}

# GET /inventory/$inventory_id
# description: expose a specific registered resource
# response:
{
    "status": 200,
    "data": [
        {
            "inventory_id": "8a526e72-bcde-45e6-8a5f-f598b350f093",
            "labels": ["nvidia"],
            "cpu_count": 12,
            "memory_gb": 32,
            "gpu": [{
                "label": "GeForce RTX 208",
                "memory_gb": 2,
            }],
            "type": "VM",
        },
    ]
}

# DELETE /allocate/$allocation_id
# description: remove (or 'free up') an allocation
# payload: {}
# response:
{
    "status": 200,
    "data": "deleted allocation",
}

# WEBSOCKET /allocate/
# description: communicate the status of an allocation
# payload:
# {
#   "requirements": {
#     "tags": ["nvidia"],
#     "username": "$host_name",
#     "allocation_timeout_seconds": 20,
#     "expires": 1576686942,
#   }
# }
# response:
{
    "status": 200,
    "data": {
        "status": "ready",
        "allocation_id": "036cf5ef-099d-4bc9-8150-82c512bd3f3c",
        "connection": {
            "host": "1.2.3.4",
            "username": "test",
            "password": "foo",
        },
        "expires": 1576688942,
    },
}

# WEBSOCKET /agent/
# allow agents to register their resources
# payload:
# {
#   "agent_id": "d4863713-1388-4297-a479-a582b306f5cb",
#   "resources": [
#        {
#            "labels": ["nvidia"],
#            "cpu_count": 12,
#            "memory_gb": 32,
#            "gpu": [{
#                "label": "GeForce RTX 208",
#                "memory_gb": 2,
#            }],
#            "type": "VM",
#        },
#   ],
# }
# response:
{
    "status": 200,
    "data": {
        "status": "ok",
    },
}
```
