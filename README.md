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

You can run all generic linters:

```sh
make lint
```

You can run individual analysis using:

```sh
make test-complexity      # run only complexity analysis
make test-security        # run only security analysis
make test-lint-python     # run only pylint
make test-lint-shellcheck # run only shell/bash linter
make test-lint-docker     # run only docker linter
```

### hwprovisoner architecture

![hwprovisioner architecture](./hwprovisioner/media/hw_provisioner.png)

Flow Diagram:

![Alt](media/automation_infra_flow_design.svg)


Directory Structure and pythonpath calculation:
All repos will be parallel to automation-infra repo.
They will have folder called automation which will be added to pythonpath automatically. Imports should be relative to that.
Inside automation folder will be another folder with the same name as the base repo (- replaced with _), and inside that relevant folders (plugins, utils, etc).

So for example the directory structure:
```
automation-infra
    automation
        automation_infra
            plugins
                ssh.py
            utils
                util1.py
            tests
                test_example.py
camera_service
    automation
        camera_service
            plugins
                camera_service.py
            utils
                cs_util.py
            tests
                test_sanity.py
pipeng
    automation
        pipeng
            plugins
                pipeng.py
            utils
                pipeng_util
            tests
...
```
And then the imports would be:
```
from automation_infra.plugins.ssh import SSH
from pipeng.plugins.pipeng import Pipeng
...
