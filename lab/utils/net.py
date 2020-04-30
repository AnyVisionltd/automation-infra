from infra.utils import shell
import logging
import netifaces
import ipaddress


def device_exists(device):
    try:
        shell.run_cmd("ip link show %s" % device, shell=True)
        return True
    except:
        return False


def delete_net_device(device):
    logging.info("Removing network device %s", device)
    shell.run_cmd("ip link del %s" % device, shell=True)


def add_macvlan_device(link_dev, macvlan_dev):
    logging.info("Add macvlan device %s to device %s", macvlan_dev, link_dev)
    shell.run_cmd(f"ip link add link {link_dev} {macvlan_dev} type macvlan mode bridge", shell=True)


def add_ip_to_device(device, ip_cidr):
    logging.info("Add ip address %s to device %s", ip_cidr, device)
    shell.run_cmd(f"ip address add {ip_cidr} dev {device}", shell=True)


def start_device(device):
    shell.run_cmd(f"ip link set dev {device} up", shell=True)


def change_route_metric_for_device(device, metric):
    cmd = f"ifmetric {device} {metric}"
    shell.run_cmd(cmd, shell=True)


def add_route(network, device, metric=None):
    logging.info("Add route %s device %s", network, device)
    cmd = f"ip route add {network} dev {device}"
    if metric is not None:
        cmd = f"{cmd} metric {metric}"
    shell.run_cmd(cmd, shell=True)


def delete_routes(device):
    logging.info("Delete routes for device %s", device)
    shell.run_cmd(f"ip route flush dev {device}", shell=True)


def default_gateway(device_name):
    gateways = netifaces.gateways()[netifaces.AF_INET]
    return [gw for gw in gateways
                            if gw[1] == device_name and gw[2] == True][0]


def network_info(device_name):
    inet_infos = netifaces.ifaddresses(device_name)
    if netifaces.AF_INET not in inet_infos:
        raise Exception("Not AF_INET info in %s" % inet_infos)
    return [ipaddress.ip_interface("%s/%s" % (ip_info['addr'], ip_info['netmask']))
             for ip_info in inet_infos[netifaces.AF_INET]]


def setup_macvlan_device(eth_device, ip_iface, macvlan_device_name):
    logging.info("Going to setup macvlan device %s for device %s info %s", macvlan_device_name, eth_device, ip_iface)
    macvlan_device_metric = 100
    try:
        add_macvlan_device(eth_device, macvlan_device_name)
        add_ip_to_device(macvlan_device_name, ip_iface.compressed)
        start_device(macvlan_device_name)
        delete_routes(macvlan_device_name)
        change_route_metric_for_device(eth_device, macvlan_device_metric + 1)
        add_route(ip_iface.network.compressed, macvlan_device_name, macvlan_device_metric)
    except:
        logging.exception("Failed to setup macvlan device %s on %s", macvlan_device_name, eth_device)
        if not device_exists(macvlan_device_name):
            return
        try:
            delete_routes(macvlan_device_name)
            delete_net_device(macvlan_device_name)
        except:
            logging.exception("Failed to delete created device", macvlan_device_name)
