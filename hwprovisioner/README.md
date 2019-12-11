hardware-provisioner
====================

This is a suite of services which manage the provisioning of hardware resources
to AnyVision employees for testing purposes.

dependencies
------------

 - `docker-compose`
 - `docker`
 - `make`

development
-----------

A convenience makefile has been provided for you. To view the list of available
options, run:

`make`

run
---

Assuming your system has all of the dependencies mentioned above, you can run
the service with:

```sh
make run
```

Once running you can view the swagger api at
[http://localhost:8080/api/v1/doc](http://localhost:8080/api/v1/doc).

Instructions for how to test the apis can be found in the swagger documentation
mentioned above. An example of how this might look would be:

```sh
curl \
  -X POST \
  --header 'Content-Type: application/json' \
  --header 'Accept: application/json' \
  -d '{ "alias": "libvirt_vagrant" }' 'http://localhost:8080/api/v1/lock/'
```

cleanup
-------

To stop and delete the containers you can run:

```sh
make cleanup
```
