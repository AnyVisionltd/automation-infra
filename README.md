automation-infra
================

make
----

A makefile has been provided for your convenience. Simply run `make` to see a
list of possible commands.

pipenv
------

If you have pipenv installed you can enter this environment with:

```sh
make shell
```

tests
-----

You can run all tests with:

```sh
make tests
```

You can run individual analysis using:

```sh
make test-complexity  # run only complexity analysis
make test-security    # run only security analysis
make test-lint-python # run only pylint
make test-lint-shellcheck # run only shell/bash linter
make test-lint-docker # run only docker linter
```

If you wish time run all of the tests together you can run:

```sh
make tests
```

### hwprovisoner architecture

![hwprovisioner architecture](./hwprovisioner/media/hw_provisioner.png)

Flow Diagram:

![Alt](media/automation_infra_flow_design.svg)
