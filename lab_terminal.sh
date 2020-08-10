#!/usr/bin/env bash



function main () {
    local cmd=$1
    local script_dir=$(dirname $(readlink -f "${BASH_SOURCE[0]}"))
    $script_dir/containerize.sh  python3 ./lab_terminal.py
}


# if script is sourced dont run dockerize
if [[ "$0" == "$BASH_SOURCE" ]]; then
    main "$*"
fi
