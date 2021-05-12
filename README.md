###### DISCLOSURE
This is an anyvision open-source project. It is written by the people for the people, if you find a bug, please fix it so everyone can benefit. And take into account that it is infrastructure, so tread softly.<br>
In other words, pull requests are happily accepted :)

## Table of Contents
- [Table of Contents](#table-of-contents)
- [Background](#background)
- [set up your environment](#set-up-your-environment)
  - [set working directory](#set-working-directory)
  - [set connection file](#set-connection-file)
  - [set docker](#set-docker)
    - [install docker](#install-docker)
- [Pytests](#pytests)
  - [Running Unprovisioned](#running-unprovisioned)
  - [Running provisioned](#running-provisioned)

## Background
The automation-infra provides an infrastructure which enables running tests on remote machines. A classic use-case 
is when developing a service which needs to run on a machine with GPU, but the developer is using a simple laptop. 

Without the automation-infra, in order to test the service, the developer will need to copy the code to a remote machine
with a GPU, deploy the service there, and then run the tests. 

Utilizing the automation-infra, the developer can specify hardware requirements for a test to run on, the infra provides
entrypoints to deploy the service before the test starts, and provides simple access to remote machines via base_config 
fixture which enable querying the service running remotely. 

This solution provides numerous advantages:
+ The test itself runs on the local machine (laptop), enabling the developer to
debug the test line by line if necessary
+ The service can be deployed and tested on any number of different hardware
+ Expensive hardware can be shared between developers developing on simple hardware and thus streamline development costs

In order to have a shared vocabulary, we will define as follows:
##### HRT 
  - Host Running Test - the local developers machine. This is the machine the test is actually running on.
##### HUT 
  - Host Under Test - the remote machine running the service we are testing.


In addition to this repository, there are 2 other infrastructure repositories: 
https://github.com/AnyVisionltd/devops-automation-infra - inits SSH communication (and more) to remote machines
https://github.com/AnyVisionltd/habertest-backend - (backend service) enables dynamic provisioning of hardware to use to run tests 
(cloud machine or on-prem).

# Directory Structure

Because the infrastructure is comprised of several repos, it is important to setup the directory structure properly. 

All repos will be parallel to automation-infra repo.
They will have folder called automation which will be added to pythonpath automatically. Imports should be relative to that.
Inside automation folder will be another folder with the same name as the base repo (- replaced with _), and inside that relevant folders (plugins, utils, etc).

Example directory structure:

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
___ ___ ___ ___ tests
___ ___ ___ ___ ___ test1.py
___ my_other_service
___ ___ automation
___ ___ ___ my_other_service
___ ___ ___ ___ plugins
___ ___ ___ ___ ___ myplugin.py
___ ___ ___ ___ tests
___ ___ ___ ___ ___ test1.py
...
```
And then the imports would be:
```
from automation_infra.plugins.ssh import SSH
from my_other_service.plugins.my_other_service import myplugin
from my_service.utils import my_util
```

# set up your environment

## set working directory

First, let's create **new** directory which will contains all the relevant git repositories for the automation tests.
why? This Directory will be the parent directory so we will be able to use your IDE to open all those repos in same window and work with the automation libraries

```
mkdir -p $HOME/workspace/automation_repos
cd $HOME/workspace/automation_repos
```

Now Let's clone the base git repo of the automation tests to the parent directory that you created above

```
git clone git@github.com:AnyVisionltd/automation-infra.git
cd automation-infra
```

Before continuing, run ./containerize.sh to make sure all basic dependencies exist. Resolve anything missing.

## set connection file

Its necessary to define the [HUT](#(HUT) ). This is done via yaml file in your `$HOME/.local/hardware.yaml` which has a structure such as:
```
host:
    ip: 192.168.xx.xxx
    user: user
    password: pass
    key_file_path: /path/to/pem
```
> key_file_path and password are mutually exclusive so use only 1 type of auth

## be a sudoer

Its necessary no to require a password when doing sudo operations. This command will make you a sudoer, ie a user who
can do sudo operations without requiring a password

```echo "$USER  ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/$USER ```

# Pytests

+ run 
  ```make test-local```
  this should pass, this means the repo and requirements are set up properly.

## Running Unprovisioned
   ```
   run/local.sh automation_infra/tests/basic_tests/test_ssh.py
   ```
   Will run the test unprovisioned according to hardware specified in `$HOME/.local/hardware.yaml`

## Running provisioned

This requires having a provisioner deployed and running at https://provisioner.tls.ai.
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

