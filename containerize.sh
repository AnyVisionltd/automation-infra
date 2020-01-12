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

function run_ssh_agent () {
	eval "$(ssh-agent -s | grep SSH)"
	ssh-add "${PUBKEY_FILE}" &>/dev/null
}

function kill_ssh_agent () {
	eval "$(ssh-agent -k &>/dev/null)"
}


function _docker_image() {
    local tag=$1
    echo "gcr.io/anyvision-training/containerize:${tag}"
}

function _docker_login() {
    local FILE=${HOME}/.gcr/docker-registry-rw.json
    if [ -e FILE ] ; then
        docker login -u _json_key -p "$(cat "$FILE")" https://gcr.io

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

    run_ssh_agent
    # Try to build
    local build_dir=$(dirname "${BASH_SOURCE[0]}")
    echo "Building docker image ${image_name}"
    DOCKER_BUILDKIT=1 \
        docker build ${docker_build_cache} -t gcr.io/anyvision-training/containerize:"${tag}" \
        --ssh default="${SSH_AUTH_SOCK}" \
        --secret id=jfrog-cfg,src="${HOME}"/.jfrog/jfrog-cli.conf \
        --label "branch_name=development" \
        --label "service_name=pipeng_devenv-${tag}" \
        -f "$build_dir"/Dockerfile_local  "$build_dir"
    kill_ssh_agent
}

function kill_container() {
    docker kill "$1" || debug_print "could not kill container $1"
}

function _add_mount() {
    echo " --volume=$1"
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

    script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
    mount_path=$(dirname "$script_dir")
    debug_print "mounting up 1 from script_dir: $mount_path"

    MOUNTS=("/dev:/dev"
            "${HOME}/.ssh:/${HOME}/.ssh"
            "/${HOME}/.netrc:/${HOME}/.netrc"
            "/var/run/docker.sock:/var/run/docker.sock"
            "${HOME}/.gitconfig:${HOME}/.gitconfig"
            "${HOME}/.jfrog:${HOME}/.jfrog"
            "$mount_path:$mount_path"
            "${HOME}/.local:${HOME}/.local"
	        )

    mount_cmd=""
    for i in "${MOUNTS[@]}"
    do
        mount_cmd+=$(_add_mount "$i")
    done
    mount_cmd+=" "

    env_cmd="-e PYTHONPATH=$script_dir"

    env_cmd="-e DISPLAY=${DISPLAY} -e CONSUL_NODE_ID=local-agent-${HOSTNAME}"

    # mount source code in same location as in host
    cmd="docker run --name ${NAME} --net=host --privileged  --rm $mount_cmd $env_cmd"

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
