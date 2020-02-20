automation-infra
================
###### DISCLOSURE
This is an anyvision open-source project. It is written by the people for the people, if you find a bug, please fix it so everyone can benefit. And take into account that it is infrastructure, so tread softly.<br>
In other words, pull requests are happily accepted :)

##Background
Directory Structure and pythonpath calculation:
All repos will be parallel to automation-infra repo.
They will have folder called automation which will be added to pythonpath automatically. Imports should be relative to that.
Inside automation folder will be another folder with the same name as the base repo (- replaced with _), and inside that relevant folders (plugins, utils, etc).

#### Set Up:
+ sudo apt-get install repo -y
+ repo init -u git@github.com:/AnyVisionltd/core-manifest.git -b hab/automation
+ repo sync -j 4
+ Put a yaml file in $HOME/.local/hardware.yaml which has similar structure to:
```
host:
    ip: 192.168.xx.xxx
    user: user
    password: pass
    key_file_path: /path/to/pem # see note below: 
```
*key_file_path and password are mutually exclusive so use only 1 type of auth

+ Get ssh docker builder key. Get this from github, details here (step 9):
https://anyvision.atlassian.net/wiki/spaces/DEV/pages/1251148648/Use+Buildkit

+ run ./run_tests.sh, this should pass, this means the repo and requirements are set up properly.

In addition, any pytest params can be used to along with the `run_tests.sh` script. A couple useful examples; 
* -h shows a help
* --pdb will drop out to pdb debugger when a test fails
* -sv will print some more logging
* pytest.ini file can be copied to test directory for realtime cli (and file) logging

Instead of using `run_tests.sh` it is also possible to use `containerize.sh` which will take you into a container with all 
settings configured and you can run whichever commands you would like inside the container.

After that, in addition you should probably clone the following repos:

**devops-automation-infra**: git@github.com:AnyVisionltd/devops-automation-infra.git<br>
**camera_service**: git@github.com:AnyVisionltd/camera-service.git<br>
**pipeng**: git@github.com:AnyVisionltd/pipeNG.git

(Make sure the repos have the subfolder automation/[repo_name]/...)

So for example the directory structure:
```
automation-infra
    automation  # <- sources root / pythonpath
        automation_infra
            plugins
                ssh.py
            utils
                util1.py
            tests
                test_example.py
devops-automation-infra
    automation  # <- sources root / pythonpath
        devops-automation_infra
            plugins
                memsql.py
                seaweed.py
            utils
                util1.py
            tests
                test_example.py
camera_service
    automation  # <- sources root / pythonpath
        camera_service
            plugins
                camera_service.py
            utils
                cs_util.py
            tests
                test_sanity.py
pipeng
    automation  # <- sources root / pythonpath
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
from camera_service.utils import cs_util
```

Anyvision Pytest plugins:
----
pytest plugins can be implemented to run custom setup/teardown logic over the infrastructure.
Core has a plugin in core-product repo, in directory core-product/automation/core_product/pytest/core_compose_v2_manager.py
It can be invoked like:  
```
./run_tests.sh -p core_product.pytest.core_compose_v2_manager /path/to/test
```
The plugin (if invoked) will copy over docker-compose-core.yaml from core-product repository (maintained by core team), 
pull and up core compose v2... So this way it is possible to run tests on a "blank" machine, which doesnt have core 
product running. 

Anyone interested to implement test setup/teardown login in addition to what is provided can implement a pytest plugin of their own and invoke it in the same way. 


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

