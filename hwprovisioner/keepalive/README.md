# "keepalive" service

It is the responsibility of the keepalive service to ensure that a particular resource remains locked to a specific user for the duration of their needs.

*Scenario: "As a developer, I want to continue using my resources, provided to me by the 'allocate' service, for as long as I need them"*

## api

```json
# WEBSOCKET /extend/
# payload:
# {
#   "allocation_id": "",
#   "origin": "$host_name + '_' + $requesting_ip",
# }
# response:
{
    "status": 200,
    "data": {
        "status": "extended",
        "expires": 1576688942,
    },
}
```

### dependencies

### running containers (with docker)

 - `docker-compose`
 - `docker`
 - `make`

### build and run locally (without docker / on host)

 - `pipenv`
 - `make`
 - `python 3.6`

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
