FROM ubuntu:18.04

RUN  apt update -y && \
     DEBIAN_FRONTEND=noninteractive apt install -y python3.7\
     libvirt-daemon python3-libvirt python3-pip iproute2 xfsprogs genisoimage\
     sudo pciutils kmod ifmetric &&\
     apt-get -y autoclean && \
     apt-get -y autoremove


RUN pip3 install aiohttp munch jinja2 PyYAML netifaces ipaddress xmltodict netaddr scapy

COPY tools/vfio-pci-bind.sh /usr/local/bin/
COPY . /root/

ENTRYPOINT ["/root/hypervisor"]
