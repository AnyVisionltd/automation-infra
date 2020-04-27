automation-infra
================
###### DISCLOSURE
This is an anyvision open-source project. It is written by the people for the people, if you find a bug, please fix it so everyone can benefit. And take into account that it is infrastructure, so tread softly.<br>
In other words, pull requests are happily accepted :)

## Table of Contents  
* [Background](#background)
* [Set Up your environment](#set-up-your-environment)
    * [set working directory](#set-working-directory)
    * [set connection file](#set-connection-file)
    * [set docker](#set-docker)
    * [set aws s3](#set-aws-s3)
    * [set git](#set-git)
* [Pytests](#pytests)
* [Provisioning](#provisioning)

## Background

Directory Structure and pythonpath calculation:
All repos will be parallel to automation-infra repo.
They will have folder called automation which will be added to pythonpath automatically. Imports should be relative to that.
Inside automation folder will be another folder with the same name as the base repo (- replaced with _), and inside that relevant folders (plugins, utils, etc).

# set up your environment

## set Make

Install make

*Ubuntu*: `sudo apt update && sudo apt -y install make`

*RHEL/CentOS*: `sudo yum -y install make`

## set working directory

First, let's create **new** directory which will contains all the relevant git repositories for the automation tests.
why? This Directory will be the parent directory so we will be able to use your IDE to open all those repos in same window and work with the automation libraries

```
mkdir -p $HOME/automation_repos
cd $HOME/automation_repos
```
> you can choose a different parent directory as much as you want

Now Let's clone the base git repo of the automation tests to the parent directory that you created above

```
git clone git@github.com:AnyVisionltd/automation-infra.git
cd automation-infra
```

## set connection file

**Makefile**

```
make -f Makefile-env set-connection-file

# OR

make -f Makefile-env set-connection-file HOST_IP=<destination host ip> USERNAME=<ssh user on destination> PASS=<ssh password on destination>

# OR

make -f Makefile-env set-connection-file HOST_IP=<destination host ip> USERNAME=<ssh user on destination> key_file_path=<ssh pem key path>
```

**or**

**Manual**

Put a yaml file in your `$HOME/.local/hardware.yaml` which has similar structure to:
```
host:
    ip: 192.168.xx.xxx
    user: user
    password: pass
    key_file_path: /path/to/pem
```
> key_file_path and password are mutually exclusive so use only 1 type of auth

## set docker

### install docker

**Makefile**
```
make -f Makefile-env docker-install
```
**or**

**Manual**

*Ubuntu*: https://docs.docker.com/install/linux/docker-ce/ubuntu

*RHEL/CentOS*: https://docs.docker.com/install/linux/docker-ce/centos

### docker login

You will need to configure **docker login credentials** in your local machine so the pytest will be able to use your **docker login credentials** in the remote host that you mentioned in the `hardware.yaml` above for docker image pull from our private docker registry (gcr)

#### docker login credentials using json file

Ask from you devops guy your **docker login credentials** `json` file

**Makefile**

```
make -f Makefile-env docker-config

# OR

make -f Makefile-env docker-config DOCKER_LOGIN_JSON_PATH=<path to json file>
```

**or**

**Manual**

```
docker login "https://gcr.io" -u _json_key -p "$(cat <path to the json file> | tr '\n' ' ')" 

# Example:
docker login "https://gcr.io" -u _json_key -p "$(cat ~/.gcr/docker-registry-ro.json | tr '\n' ' ')"
```

## set aws s3

### install aws cli

**Makefile**

```
make -f Makefile-env aws-install
```

**or**

**Manual**

*Ubuntu / RHEL / CentOS*: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-linux.html

> You will need to install `unzip` prior the `aws cli` installation


### aws config credentials

Ask from you devops guy your **aws login credentials**, you should get: `aws access key` and `aws secret key`

**Makefile**

```
make -f Makefile-env aws-config
# OR
make -f Makefile-env aws-config S3_KEY=<access key> S3_SECRET=<secret key>
```
>  you can use also `S3_REGION=<region>` (default: `eu-central-1`)

**or**

**Manual**

set you aws config by running:

```
aws configure set aws_access_key_id <aws_access_key_id>
aws configure set aws_secret_access_key <aws_secret_access_key>
aws configure set default.region eu-central-1
```

## set git

### install git cli

**Makefile**

```
make -f Makefile-env git-install
```

**or**

**Manual**

*Ubuntu / RHEL / CentOS*: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git

### configure git credentials

**github**:

*token*: https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line

or

*ssh key*: https://help.github.com/en/enterprise/2.15/user/articles/adding-a-new-ssh-key-to-your-github-account 

## git repositories

Let's `git pull` all the relevant git repositories by product

Now we can pull all the relevant git repositories by product

**Makefile**

```
make -f Makefile-env git-pull

# OR

make -f Makefile-env git-pull PRODUCT=<product name>

# OR clone using url instead of ssh

make -f Makefile-env git-pull PRODUCT=<product name> CLONE_METHOD=url

# OR clone using url instead of ssh and set user and token

make -f Makefile-env git-pull PRODUCT=<product name> CLONE_METHOD=url GIT_USER=<user> GIT_TOKEN=<token>
```
**or**

**Manual**

git clone each line in $HOME/automation_repos/dev_environment/{product name}.txt
```

cat $HOME/automation_repos/automation-infra/dev_environment/{product name}.txt
git clone -C $HOME/automation_repos/automation-infra {line}

# Example:
cat $HOME/automation_repos/dev_environment/core.txt
# Output:
git@github.com:AnyVisionltd/devops-automation-infra.git
git@github.com:AnyVisionltd/camera-service.git
git@github.com:AnyVisionltd/pipeng.git
git@github.com:AnyVisionltd/protobuf-contract.git
git@github.com:AnyVisionltd/core-products.git

# clone:
git -C $HOME/automation_repos clone git@github.com:AnyVisionltd/devops-automation-infra.git
git -C $HOME/automation_repos clone git@github.com:AnyVisionltd/camera-service.git
git -C $HOME/automation_repos clone git@github.com:AnyVisionltd/pipeng.git
git -C $HOME/automation_repos clone git@github.com:AnyVisionltd/protobuf-contract.git
git -C $HOME/automation_repos clone git@github.com:AnyVisionltd/core-product.git
```

At the end you will get this directory structure for **core** product
```
automation_repos
├── automation-infra
├── camera-service
├── core-product
├── devops-automation-infra
├── pipeng
└── protobuf-contract
```


# Pytests

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


# Provisioning

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

## hwprovisoner architecture

https://anyvision.atlassian.net/wiki/spaces/PROD/pages/1558806855

## run backend services

These steps will allow you to run allocate, redis and a resource manager:

It is recommended you start by copying
`./hwprovisioner/resourcemanager/example.resources.yml` to
`./hwprovisioner/resourcemanager/resources.yml` and update the content to
match the resources you have.


```sh
# note: RESOURCES_CONFIG_FILE is relative to ./hwprovisioner/resourcemanager/
RESOURCES_CONFIG_FILE=./resources.yml make run-server
```
