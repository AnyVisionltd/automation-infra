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

You can run only the unit tests with:

```sh
make test
```

Additional analysis tools have been provided with:

```sh
make test-complexity  # run only complexity analysis
make test-security    # run only security analysis
make test-lint-python # run only pylint
make test-lint-docker # run only docker
```

If you wish time run all of the tests together you can run:

```sh
make tests
```
