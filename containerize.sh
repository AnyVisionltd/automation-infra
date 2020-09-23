#!/usr/bin/env bash

set -eu

PUBKEY_FILE=/${HOME}/.ssh/docker-builder-key
DOCKERIZE_FORCE_BUILD=${DOCKERIZE_FORCE_BUILD:-0}

# Absolute path to this script
SCRIPT=$(readlink -f "${BASH_SOURCE[0]}")
# Absolute path to the script directory
script_dir=$(dirname "$SCRIPT")
MOUNT_PATH="${MOUNT_PATH:-$(dirname "$script_dir")}"
V=${V:=0}

function _is_debug() {
   if [ "$V" == "1" ];
   then
      echo "1"
   else
      echo "0"
   fi
}

function debug_print() {
    if [ "$V" = "1" ]; then echo "$1"; fi
}

function docker_tag () {
    local current_file=${BASH_SOURCE[0]}
    local current_dir=$(dirname "$current_file")
    local files_sum
    local total_sum

    HASH_FILES=($current_dir/Dockerfile_local ${BASH_SOURCE[0]})
    HASH_FILES+=($current_dir/requirements3.txt $current_dir/entrypoint.sh)

    if command -v md5sum > /dev/null 2>&1; then
      files_sum="$(md5sum -- ${HASH_FILES[@]} | awk {'print $1'})"
      total_sum="$(md5sum <<< "$files_sum")"
    elif command -v md5 > /dev/null 2>&1; then
      files_sum="$(md5 -q ${HASH_FILES[@]} | awk {'print $1'})"
      total_sum="$(md5 <<< "$files_sum")"
    else
      >&2 echo "ERROR: please install md5 nor md5sum!"
      exit 1
    fi
    echo $total_sum | awk '{print substr($1,1,12)}'
}

function run_ssh_agent () {
    if [ -e $PUBKEY_FILE ] ; then
        eval "$(ssh-agent -s | grep SSH)"
        ssh-add "${PUBKEY_FILE}" &>/dev/null
    else
        >&2 echo "couldnt PUBKEY_FILE for ssh-agent"
        exit 1
    fi
}

function kill_ssh_agent () {
    eval "$(ssh-agent -k &>/dev/null)"
}


function _docker_image() {
    local tag=$1
    echo "gcr.io/anyvision-training/automation-infra:${tag}"
}

function _docker_login() {
    local DOCKER_CONFIG=${HOME}/.docker/config.json
    local FILE=${HOME}/.gcr/docker-registry-rw.json
    if [ ! -f $DOCKER_CONFIG ]; then
        if [ -f $FILE ] ; then
            docker login -u _json_key -p "$(cat "$FILE")" https://gcr.io
        else
            >&2 echo "didnt find docker-registry-rw file! "
            exit 1
        fi
    fi

}

function build_docker_image () {
    local tag=$1
    local image_name=$(_docker_image "${tag}")
    local docker_build_cache=""

    if [ "${DOCKERIZE_FORCE_BUILD}" == "0" ];
    then
        if docker inspect --type=image "${image_name}" &>/dev/null;
        then
           debug_print "image found locally ${image_name}"
           return
        fi
        debug_print "image not found locally, try to pull image from registry"
        _docker_login
        if docker pull "$image_name";
        then
           debug_print "image pulled ${image_name}"
           return
        fi
    else
        docker_build_cache="--no-cache"
    fi

    # Try to build
    local build_dir=$(dirname "${BASH_SOURCE[0]}")
    echo "Building docker image ${image_name}"
    DOCKER_BUILDKIT=1 \
        docker build ${docker_build_cache} -t "${image_name}" \
        --label "service_name=automation-infra" \
        --label "tag=${tag}" \
        -f "$build_dir"/Dockerfile_local "$build_dir" \
        --network=host
}

function kill_container() {
    docker kill "$1" || debug_print "could not kill container $1"
}

function _add_mount() {
    if command -v gravity > /dev/null 2>&1 && \
        gravity status | grep -i 'Status:' | grep -i -q 'active'; then
        echo " --volume=/host$1"
    else
        echo " --volume=$1"
    fi
}

function _read_passed_environment() {
    local current_file=${BASH_SOURCE[0]}
    local current_dir=$(dirname "$current_file")

    env_variable_cmd=""
    while IFS='=' read -r key value; do
        local value=$(eval echo "${value}")
        if [ -n "$value" ];
        then
           env_variable_cmd+=" -e ${key}=$(eval echo "${value}")"
        fi
    done < "${current_dir}"/pass_environment
    echo "${env_variable_cmd}"
}

function add_subdirs_from_path () {
    local base_path=$1
    if [ -d $base_path ]; then
        local res_path=""
        for file in $(ls $base_path);
        do
            res_path+=":$base_path/$file/automation"
            if [ $file = "protobuf-contract" ]; then
                file="$file/build/python"
                res_path+=":$base_path/$file"
            fi
        done
        echo $res_path
    else
        >&2 echo "not valid path directory"
        exit 1
    fi
}

function build_python_path () {
    local mount_path=$1
    local python_path=""
    for file in $(ls $mount_path);
        do
            if [ $file = "protobuf-contract" ]; then
                file="$file/build/python"
                python_path+=":$mount_path/$file"
            elif [ $file = "automation-infra" ]; then
                python_path+=":$mount_path/$file"
            else
                python_path+=":$mount_path/$file/automation"
            fi

    done
    echo $python_path
}

function run_docker () {
    local tag="$1"
    local run_cmd="$2"

    ps -o stat= -p $$ | grep -q + || INTERACTIVE=false
    # if we do not have terminal - no need to allocate one
    # this is useful when running dockerize make inside vim
    [ -t 1 ] || INTERACTIVE=false
    INTERACTIVE=${INTERACTIVE:-true}

    # We generate a unique name in order to be able to kill the container when the terminal is closed.
    NAME=$(uuidgen)

    # I dont think this is necessary because docker is run with --rm but am leaving it to make sure
    # trap "kill_container ${NAME}" 0

    MOUNTS=("${HOME}/.ssh:${HOME}/.ssh"
            "/var/run/docker.sock:/var/run/docker.sock"
            "${HOME}/.local/hardware.yaml:${HOME}/.local/hardware.yaml"
            "${HOME}/.docker:${HOME}/.docker"
            "${HOME}/.aws:${HOME}/.aws"
            "${HOME}/.npmrc:${HOME}/.npmrc"
            "${HOME}/.helm:${HOME}/.helm"
            "$MOUNT_PATH:$MOUNT_PATH"
            "/etc/localtime:/etc/localtime:ro"
	        )

    mount_cmd=""
    for i in "${MOUNTS[@]}"
    do
        mount_cmd+=$(_add_mount "$i")
    done
    mount_cmd+=" "

    python_path=$(build_python_path $MOUNT_PATH)

    env_cmd+="-e PYTHONPATH=${python_path} "

    # mount source code in same location as in host
    cmd="docker run -t --name ${NAME} --privileged  --rm --cap-add=SYS_PTRACE --security-opt seccomp=unconfined $mount_cmd $env_cmd"

    cmd+=" $(_read_passed_environment)"

    if [ $INTERACTIVE = true ] ; then
        cmd+=" -it"
    fi

    # set workdir as current dir
    cmd+=" --workdir=${PWD}"

    cmd+=" $(_docker_image "${tag}")"

    if [ -n "$run_cmd" ] ; then
        cmd+=" $run_cmd"
    fi

    debug_print "Executing ${cmd}"
    ${cmd}
}


function main () {
    local cmd="$1"
    debug_print "running script with command args: $cmd"
    local tag=$(docker_tag)
    build_docker_image "$tag"
    run_docker "$tag" "$cmd"
}

cmd=${1:-"bash"}

# If just asking for help
if [ "$cmd" == "-h" ] || [ "$cmd" == "--help" ]; then
  echo "Use: V=1 $(basename "$0") for debug printing"
  echo "Just running $(basename "$0") will default to $(basename "$0") bash"
  echo "Or use $(basename "$0") and any args which docker run will accept"
fi

# if script is sourced dont run dockerize
if [ "$0" == "$BASH_SOURCE" ]; then
    main "$*"
fi
