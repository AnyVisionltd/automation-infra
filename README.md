# Automation labs Confluence space:

https://anyvision.atlassian.net/wiki/spaces/PROD/pages/1558806832/Automation+Labs

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

## Quickstart for aws provisioning:
* Make sure `~/.docker/config.json` exists and you can pull anyvision containers from gcr.
* Make sure you have `~/.ssh/anyvision-devops.pem` (talk to devops if you need it).
* Put cert files in place acc to these instructions:
https://anyvision.atlassian.net/wiki/spaces/PROD/pages/2266464264/Run+test+with+cloud+provisiner
* run: `./run/aws.sh automation_infra/tests/basic_tests/test_ssh.py`. This should pass, otherwise something isn't set up properly.

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

Instructions for setting up docker credentials: 
https://anyvision.atlassian.net/wiki/spaces/INTEGRATION/pages/752321438/Software+Installation+from+scratch

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

+ run 
  ```make test-sanity```
  this should pass, this means the repo and requirements are set up properly.
if you get an error "sudo: a terminal is required..." then you need to be a sudoer. something like this should do the 
trick (obv change 'user' with your username):
```echo "user  ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/user ```
  
./run folder:
+ there is a run folder which has various shell scripts in it, aws.sh, local.sh, etc
+ These are helper scripts which wrap calls to pytest invoking various infrastructure plugins automatically, so that it wont be necessary to write out tedious commands when trying to run a test.
+ the Makefile has various targets which can be used as examples as to how the run bash scripts can be invoked. 
+ there are ./run/\<script>.sh scripts also in devops-infra (and core-product) repos which can be used as well to invoke devops (and core) plugins automatically. If you are working on a different repo which doesnt have helper scripts yet, you are welcome to add them to make it easy for other developers to write tests simply by automatically invoking relevant plugins.


  
So for example the directory structure:
```
___ automation-infra                                                                                                                                                                                               
___ ___ automation_infra             
___ ___ ___ plugins       
___ ___ ___ ___ ssh.py       
___ ___ pytest_automation_infra
___ ___ ___ unit_tests
___ ___ run      
___ camera-service
___ ___ automation
___ ___ ___ camera_service
___ ___ ___ ___ utils
___ ___ ___ ___ ___ cs_util.py
___ pipeNG
___ ___ automation
___ ___ ___ pipeng
___ ___ ___ ___ plugins
___ ___ ___ ___ ___ pipeng.py
___ ___ ___ devops_docker_installer
___ ___ ___ devops_proxy_container
___ ___ ___ proxy_container
___ ___ run
...
```
And then the imports would be:
```
from automation_infra.plugins.ssh import SSH
from pipeng.plugins.pipeng import Pipeng
from camera_service.utils import cs_util
```

