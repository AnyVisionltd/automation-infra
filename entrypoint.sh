#!/bin/bash

function add_user() {
    adduser --home "${userhome}" --disabled-password  --uid "${uid}" --gecos '' "${username}" &>/dev/null
    adduser "${username}" sudo &>/dev/null
    touch "${userhome}"/.sudo_as_admin_successful
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
    ln -s /tmp/home_bin "${userhome}"/bin
    gpasswd -a "${username}" docker &>/dev/null
    chown "${username}":"${username}" "${userhome}"
    usermod -aG docker "${username}"
    usermod -aG video "${username}"
}


echo 'source /environ ' >> "${userhome}"/.bashrc
add_user
# We need to adjust docker group according to GID on the host machine
# so that we will be able to run docker inside docker
groupmod -g "${DOCKER_GROUP_ID}" docker

if [ "x$*" != "xbash" ]; then
    su "${username}" -c -- "$*"
else
    su "${username}"
fi
