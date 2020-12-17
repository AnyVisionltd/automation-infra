#!/usr/bin/env bash

if [ "$1" == "-h" ]; then
  printf "\nWill run supplied test using locally configured hardware on hardware.yaml\n"
  printf "\nExample usage:\n./run/aws.sh /path/to/tests --any --other --pytest --flags --you --like\n\n"
  exit 0
fi

script_dir=$(dirname $(readlink -f "${BASH_SOURCE[0]}"))
prefix="$script_dir/../containerize.sh python -m pytest -p pytest_automation_infra -s "
echo "running command: $prefix $@"
sleep 3
$prefix $@