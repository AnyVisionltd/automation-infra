#!/usr/bin/env python3 
import requests
import argparse
import functools
import json

CLOUD_PROVIDER = "Google"
OS_NAME = "ubunut1804"
RAM_SIZE = 32
SSD_SIZE = 100
STORAGE_SIZE = 500
CPU_COUNT = 8
GPU_COUNT = 1
GPU_TYPE = "k80"


def _do_provision(args):
    data = {"base_image": args.os,
            "ram" : args.ram,
            "num_cpus": args.cpus,
            "num_gpus" : args.gpus,
            "ssd" : args.ssd,
            "storage": args.storage,
            "gputype": args.gpu_type}

    return requests.post("http://%s/provision" % args.allocator, json=data)


def _do_destroy(args):
    return requests.delete("http://%s/vms/%s" % (args.allocator, args.name))


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
    create.add_argument("--os", help="VM Operating System: %s" % OS_NAME, default=OS_NAME)
    create.add_argument("--ram", help="Ram in GBytes: %i" % RAM_SIZE, type=int, default=RAM_SIZE)
    create.add_argument("--ssd", help="SSD disk in Gbytes %i" % SSD_SIZE, type=int, default=SSD_SIZE)
    create.add_argument("--storage", help="Storage HDD disk in Gbytes %i" % STORAGE_SIZE, type=int, default=STORAGE_SIZE)
    create.add_argument("--cpus", help="Instance CPU`s Number %i" % CPU_COUNT, type=int, default=CPU_COUNT)
    create.add_argument("--gpus", help="Instance GPU`s number %i" % GPU_COUNT, type=int, default=GPU_COUNT)
    create.add_argument("--gpu_type", help="Instance GPU Type %s" % GPU_TYPE, default=GPU_TYPE)

    create = commands.add_parser("destroy", help="Destroy VM Instance")
    create.add_argument("--name", help="Name of the VM Instance to delete", required=True)

    create = commands.add_parser("images", help="List images")
    create = commands.add_parser("list", help="List vms")

    # create = commands.add_parser('poweroff', help="Poweroff VM")
    # create.add_argument('--name', help="Name of the VM to poweoff", required=True)

    # create = commands.add_parser('poweron', help="Poweron VM")
    # create.add_argument('--name', help="Name of the VM to poweron", required=True)

    create = commands.add_parser('info', help="Get VM Instance information")
    create.add_argument('--name', help="Name of the VM", required=True)

    commands = {"provision" : _do_provision,
                "destroy" : _do_destroy,
                "images" : _do_list_images,
                "list"   : _do_list_vms,
                "poweroff" : functools.partial(_do_update_vm, status = {"power" : "off"}),
                "poweron" : functools.partial(_do_update_vm, status = {"power" : "on"}),
                "info" : _do_vm_info}

    args = parser.parse_args()
    result = commands[args.command](args)
    if result.ok:
        print(json.dumps(result.json()))
    else:
        print("Command failed status: %s" %result.status_code)
