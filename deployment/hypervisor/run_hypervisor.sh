#!/bin/bash 
set -e

RUN_IMAGES_DIR="${RUN_IMAGES_DIR:-/home/sashas/workspace2/run_images}"
BASE_IMAGE_DIR="${BASE_IMAGE_DIR:-/home/sashas/workspace2/images}"
SSD_IMAGES_DIR="${SSD_IMAGES_DIR:-/home/sashas/workspace2/ssd_images}"
HDD_IMAGES_DIR="${HDD_IMAGES_DIR:-/home/sashas/workspace2/hdd_images}"
CONFIG_FILE="${CONFIG_FILE:-/home/sashas/workspace2/automation-infra/config/hypervisor.yaml}"
MAX_VMS="${MAX_VMS:-1}"
LOG_LEVEL="${LOG_LEVEL:-DEBUG}"
PARAVIRT_NET_DEVICE="${PARAVIRT_NET_DEVICE:-enp0s31f6}"
SOL_PORT="${SOL_PORT:-10000}"
HOSTNAME=$(hostname)
KERNEL_LIBS=/lib/modules/$(uname -r)
LIBVIRT_SOCK=/var/run/libvirt/libvirt-sock

MOUNTS=("$RUN_IMAGES_DIR:$RUN_IMAGES_DIR"
        "${BASE_IMAGE_DIR}:${BASE_IMAGE_DIR}:ro"
        "${SSD_IMAGES_DIR}:${SSD_IMAGES_DIR}"
        "${HDD_IMAGES_DIR}:${HDD_IMAGES_DIR}"
        "${LIBVIRT_SOCK}:${LIBVIRT_SOCK}"
        "/dev:/dev"
        "${CONFIG_FILE}:/root/config.yaml:ro"
        "${KERNEL_LIBS}:${KERNEL_LIBS}")

mounts_cmd=""
for i in "${MOUNTS[@]}"
do
    mounts_cmd+=" -v $i "
done
mounts_cmd+=" "

params="--config=/root/config.yaml --images-dir=${BASE_IMAGE_DIR} --run-dir=${RUN_IMAGES_DIR} \
--ssd-dir=${SSD_IMAGES_DIR} --hdd-dir=${HDD_IMAGES_DIR} --log-level=${LOG_LEVEL} --max-vms=${MAX_VMS} \
--paravirt-net-device=${PARAVIRT_NET_DEVICE} --sol-port=${SOL_PORT} --server-name=${HOSTNAME}"


docker run -d --net=host --privileged --restart=always --log-driver=syslog --log-opt tag=HYPERVISOR \
${mounts_cmd} hypervisor:latest ${params}

