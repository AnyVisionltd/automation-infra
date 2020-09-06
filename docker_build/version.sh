#!/bin/bash

function docker_tag () {
    local current_file=${BASH_SOURCE[0]}
    local current_dir=$(dirname $current_file)
    local dockerfile=${current_dir}/Dockerfile

    HASH_FILES=(${BASH_SOURCE[0]} $current_dir/requirements.txt $current_dir/docker_user.pem $current_dir/docker_user.pem.pub)
    local files_sum="$(md5sum -- ${HASH_FILES[@]} | awk {'print $1'})"
    local total_sum="$(echo -n $files_sum | md5sum | awk '{print substr($1,1,12)}')"
    echo $total_sum
}

docker_tag 