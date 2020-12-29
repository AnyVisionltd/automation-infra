#!/usr/bin/env bash

if [ "$1" == "-h" ]; then
  printf "\nWill run suppled test using aws provisioner\n"
  printf "\nExample usage:\n./run/aws.sh /path/to/tests --any --other --pytest --flags --you --like\n\n"
  exit 0
fi

script_dir=$(dirname $(readlink -f "${BASH_SOURCE[0]}"))
prefix="$script_dir/../containerize.sh python -m pytest -p provisioner --provisioner=https://provisioner.tls.ai --heartbeat=https://heartbeat-server.tls.ai --ssl-cert=$HOME/.habertest/habertest.crt --ssl-key=$HOME/.habertest/habertest.key -s "
echo "running command: $prefix $@"
sleep 3
$prefix "$@"