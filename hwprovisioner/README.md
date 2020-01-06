hardware-provisioner
====================

This is a suite of services which manage the provisioning of hardware resources to AnyVision employees for testing purposes.

## commands

For your convenience, several commands have been added to this directory for you. You can avail of these by running `make <command>`, e.g. `make tests`

```shell
$ make
run                            runs the application in docker-compose
tests                          run all modules tests sequentially
shell                          runs pipenv shell
lint                           run all modules linters sequentially
test-complexity                run only python complexity analysis
test-security                  run only python security analysis
test-lint-docker               run only docker linter
test-lint-shellcheck           run only shell/bash linter
clean                          clean up environment
```

**note:** each sub-directory also has it's own set of commands.

## architecture

![https://drive.google.com/open?id=1BOZt_jmk6GO5P5vGxP0tcgFOGRkaa5bB](./media/hw_provisioner.png)
