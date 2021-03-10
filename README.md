# Automation labs Confluence space:

###### DISCLOSURE
This is an anyvision open-source project. It is written by the people for the people, if you find a bug, please fix it so everyone can benefit. And take into account that it is infrastructure, so tread softly.<br>
In other words, pull requests are happily accepted :)

## Table of Contents  
- [Automation labs Confluence space:](#automation-labs-confluence-space)
          - [DISCLOSURE](#disclosure)
  - [Table of Contents](#table-of-contents)
  - [Background](#background)
- [set up your environment](#set-up-your-environment)
  - [set Make](#set-make)
  - [set working directory](#set-working-directory)
  - [set connection file](#set-connection-file)
  - [set docker](#set-docker)
    - [install docker](#install-docker)
- [Pytests](#pytests)
  - [Running Unprovisioned](#running-unprovisioned)
  - [Running provisioned](#running-provisioned)

## Background
This project aim is to connect a any *Linux* running hardware that has SSH acess with pytest testing framework.
There are 2 ways to write and run tests
* Unprovisioned - In this case you specify the hardware in hardware.yaml file see (#hardware-yaml) section
* Provisioned - You need "provisioner" installed (#running-provisioned)

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

# Pytests

+ run 
  ```make test-local```
  this should pass, this means the repo and requirements are set up properly.
if you get an error "sudo: a terminal is required..." then you need to be a sudoer. something like this should do the 
trick (obv change 'user' with your username):
```echo "user  ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/user ```
## Running Unprovisioned
   ```
   run/local.sh automation_infra/tests/basic_tests/test_ssh.py
   ```
   Will run the test unprovisioned according to hardware specified in `$HOME/.local/hardware.yaml`

## Running provisioned
   ```
   run/aws.sh automation_infra/tests/basic_tests/test_ssh.py
   ```
   Assume that you have provisioner, it will provision the machine and run the test on the provisoner
   Look at documentation of habertest-backend project to learn more on how to install provisioner

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
___ my_service
___ ___ automation
___ ___ ___ my_service
___ ___ ___ ___ utils
___ ___ ___ ___ ___ my_util.py
___ my_other_service
___ ___ automation
___ ___ ___ my_other_service
___ ___ ___ ___ plugins
___ ___ ___ ___ ___ myplugin.py
...
```
And then the imports would be:
```
from automation_infra.plugins.ssh import SSH
from my_other_service.plugins.my_other_service import myplugin
from my_service.utils import my_util.py
```
