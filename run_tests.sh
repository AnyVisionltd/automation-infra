#!/usr/bin/env bash

function _is_debug() {
   if [ "$V" == "1" ];
   then
      echo "1"
   else
      echo "0"
   fi
}

function debug_print() {
    if [ "$(_is_debug)" == "1" ]
    then
       echo "$1"
    fi
}


function update_received_cmd () {
    # Adds -p pytest_local_init if neither infra plugin is specified, or pytest_automation_infra if -n is specified
    # Adds --forked arg always because I want the tests to be run in separate process
    # Also there is room to add here other arg parsing we want to do with infra.
    local cmd=$1

    if [[ $cmd != " python "* ]] && [[ $cmd != " pytest "* ]] ; then
      cmd="python -m pytest $cmd"
    fi

    if [[ $cmd != *" -p "* ]] ; then
        cmd="$cmd -p pytest_automation_infra"
    fi

    if [[ $cmd = *" -n"?(\ )[0-9]* ]] && [[ $cmd != *" --provisioned"* ]] ; then
        cmd="$cmd --provisioned"
    fi

    cmd="$cmd --ignore=lab --ignore=hwprovisioner"

    echo "$cmd"
}


function main () {
    local cmd=$1
    echo "received command: $cmd"
    cmd=$(update_received_cmd "$cmd")
    echo "after updating received command: $cmd"
    echo "running command: ./containerize.sh $cmd"
    ./containerize.sh "$cmd"
}


# If just asking for help
if [ "$1" == "-h" ]; then
  echo "Arguments are attempted to be parsed intelligently and automatically by adding python -m pytest if not specified"
  echo "If provisioned isnt specified (--provisioned arg), will try to run locally (must have hardware.yaml file)"
  echo "--forked is added automatically to run tests in a forked subprocess"
  echo "Can specify run in parallel with -n NUM. Will use provisioner (cant run local)"
  echo "Can specify tests with regular pytest syntax: test_module.py::test_name"
  echo "Use: V=1 $(basename "$0") for debug printing"
  echo "Or use any additional pytest run args, ex: $(basename "$0") --html=report.html --self-contained-html"
  read -p "Show pytest help? (y/n) " -t 5 yn
  case $yn in
        [Yy]* ) pytest -h;;
        * ) exit;;
  esac
  exit 0
fi


# if script is sourced dont run dockerize
if [[ "$0" == "$BASH_SOURCE" ]]; then
    main "$*"
fi
