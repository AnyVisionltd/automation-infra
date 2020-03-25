#!/usr/bin/env python3 
import requests
import argparse
import functools
import json

CLOUD_PROVIDER = "AWS"
OS_NAME = "ubuntu-1804-lts"
INSTANCE_TYPE = "g4dn.xlarge"
SSD_SIZE = 100
STORAGE_SIZE = 500
REGION_NAME = "eu-west-3"


def _do_provision(args):
    data = {"os_type": args.os_type,
            "customer_name": args.customer_name,
            "provider": args.provider,
            "region": args.region,
            "instance_type": args.instance_type,
            "ssd_ebs_size": args.ssd,
            "storage_ebs_size": args.storage}

    return requests.post("http://%s/provision" % args.allocator, json=data)


def _do_destroy(args):
    data = {"region": args.region, "customer_name": args.customer_name}
    return requests.post("http://%s/destroy" % args.allocator, json=data)


def _do_list_images(args):
    return requests.get("http://%s/images" % (args.allocator))


def _do_list_vms(args):
    return requests.get("http://%s/vms" % (args.allocator))


def _do_update_vm(args, status):
    return requests.post("http://%s/vms/%s/status" % (args.allocator, args.name), json=status)


def _do_vm_info(args):
    return requests.get("http://%s/vms/%s" % (args.allocator, args.name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--allocator", help="Allocator host:port", required=True)
    commands = parser.add_subparsers(title="command", dest="command")
    commands.required = True

    create = commands.add_parser("provision", help="Provision VM Instance")
    create.add_argument("--provider", help="Cloud Provider: %s" % CLOUD_PROVIDER, default=CLOUD_PROVIDER)
    create.add_argument("--customer_name", help="Customer Name", required=True)
    create.add_argument("--os_type", help="VM Operating System: %s" % OS_NAME, default=OS_NAME)
    create.add_argument("--region", help="Instance Region: %s" % REGION_NAME, default=REGION_NAME)
    create.add_argument("--instance_type", help="Instance Type: %s" % INSTANCE_TYPE, default=INSTANCE_TYPE)
    create.add_argument("--ssd", help="SSD disk in Gbytes %i" % SSD_SIZE, type=int, default=SSD_SIZE)
    create.add_argument("--storage", help="Storage HDD disk in Gbytes %i" % STORAGE_SIZE, type=int,
                        default=STORAGE_SIZE)

    create = commands.add_parser("destroy", help="Destroy Instance")
    create.add_argument("--region", help="Instance Region", required=True)
    create.add_argument("--customer_name", help="Customer Name", required=True)

    create = commands.add_parser('info', help="Get VM Instance information")
    create.add_argument('--name', help="Name of the VM", required=True)

    commands = {"provision": _do_provision,
                "destroy": _do_destroy }

    args = parser.parse_args()
    result = commands[args.command](args)
    if result.ok:
        print(json.dumps(result.json()))
    else:
        print("Command failed status: %s" % result.status_code)
