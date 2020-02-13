#!/bin/bash

set -eu

PUBKEY_FILE=/${HOME}/.ssh/docker-builder-key
DOCKERIZE_FORCE_BUILD=${DOCKERIZE_FORCE_BUILD:-0}
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
    if [ "$(_is_debug)" == "1" ]
    then
       echo "$1"
    fi
}

function docker_tag () {
    local current_file=${BASH_SOURCE[0]}
    local current_dir=$(dirname "$current_file")

    HASH_FILES=($current_dir/Dockerfile_local ${BASH_SOURCE[0]})
    HASH_FILES+=($current_dir/requirements3.txt $current_dir/entrypoint.sh)

    local files_sum="$(md5sum -- ${HASH_FILES[@]} | awk {'print $1'})"
    local total_sum="$(md5sum <<< "$files_sum" | awk '{print substr($1,1,12)}')"
    echo "$total_sum"
}
IMAGE_NAME="${IMAGE_NAME:-gcr.io/anyvision-training/containerize:$(docker_tag)}"

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

function build_docker_image () {
    run_ssh_agent
    # Try to build
    local build_dir=$(dirname "${BASH_SOURCE[0]}")
    echo "Building docker image ${IMAGE_NAME}"
    DOCKER_BUILDKIT=1 \
        docker build -t $IMAGE_NAME \
        --ssh default="${SSH_AUTH_SOCK}" \
        --secret id=jfrog-cfg,src="${HOME}"/.jfrog/jfrog-cli.conf \
        -f "$build_dir"/Dockerfile_local  "$build_dir"
    kill_ssh_agent
}

function _add_mount() {
    echo " --volume=$1"
}


function _read_passed_environment() {
    local current_file=${BASH_SOURCE[0]}
    local current_dir=$(dirname "$current_file")

    env_variable_cmd=""
    set +u
    while IFS='=' read -r key value; do
        local value=$(eval echo "${value}")
        if [ -n "$value" ];
        then
           env_variable_cmd+=" -e ${key}=$(eval echo "${value}")"
        fi
    done < "${current_dir}"/pass_environment
    set -u
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

function run_docker () {
    local run_cmd="$1"

    ps -o stat= -p $$ | grep -q + || INTERACTIVE=false
    # if we do not have terminal - no need to allocate one
    # this is useful when running dockerize make inside vim
    [ -t 1 ] || INTERACTIVE=false
    INTERACTIVE=${INTERACTIVE:-true}

    MOUNTS=("/dev:/dev"
            "${HOME}/.ssh:${HOME}/.ssh"
            "/${HOME}/.netrc:${HOME}/.netrc"
            "/var/run/docker.sock:/var/run/docker.sock"
            "${HOME}/.gitconfig:${HOME}/.gitconfig"
            "${HOME}/.jfrog:${HOME}/.jfrog"
            "${PWD}:${PWD}"
            "${HOME}/.local:${HOME}/.local"
	        )

    mount_cmd=""
    for i in "${MOUNTS[@]}"
    do
        mount_cmd+=$(_add_mount "$i")
    done
    mount_cmd+=" "

    # mount source code in same location as in host
    cmd="docker run --rm --privileged $mount_cmd"

    cmd+=" $(_read_passed_environment)"

    if [ $INTERACTIVE = true ] ; then
        cmd+=" -it"
    fi

    # set workdir as current dir
    cmd+=" --workdir=${PWD}"

    cmd+=" $IMAGE_NAME"

    if [ -n "$run_cmd" ] ; then
        cmd+=" $run_cmd"
    fi

    debug_print "Executing ${cmd}"
    ${cmd}
}


function main () {
    local cmd="$1"
    debug_print "running script with command args: $cmd"
    build_docker_image
    run_docker "$cmd"
}

cmd=${1:-"bash"}

# If just asking for help
if [ "$cmd" == "-h" ]; then
  echo "Use: V=1 $(basename "$0") for debug printing"
  echo "Just running $(basename "$0") will default to $(basename "$0") bash"
  echo "Or use $(basename "$0") and any args which docker run will accept"
  exit
fi

# if script is sourced dont run dockerize
if [ "$0" == "$BASH_SOURCE" ]; then
    main "$*"
fi
