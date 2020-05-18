hypervisor
==========

server
------

To run the hypervisor server, first ensure you have the docker image,
(`make build-hypervisor`), then you can run the server:

```sh
RUN_IMAGES_DIR=/home/pathto/images-run/ \
BASE_IMAGE_DIR=/home/pathto/images \
SSD_IMAGES_DIR=/home/pathto/images-ssd/ \
HDD_IMAGES_DIR=/home/pathto/images-hdd/ \
PARAVIRT_NET_DEVICE=yourNetworkDeviceId0 \
CONFIG_FILE=/home/pathto/config/hypervisor.yaml \
./deployment/hypervisor/run_hypervisor.sh
```

To view logs you can run `tail -f /var/log/syslog` or view it in journalctl

client
------

you should now be able to run the client:

```sh
./hypervisor_cli.py --allocator=localhost:8080 create \
  --image debian \ # $BASE_IMAGE_DIR/debian.qcow2
  --ram 2 \
  --cpus 2 \
  bridge # network. bridge or isolated
```
