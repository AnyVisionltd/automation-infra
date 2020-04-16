#!/usr/bin/env python3 
import requests
import argparse
import functools
import json


def _do_create(args):
    data = {"base_image": args.image,
            "ram" : args.ram,
            "num_cpus": args.cpus,
            "networks" : args.networks_all,
            "num_gpus" : args.gpus,
            "disks" : [] }

    if args.ssd:
        data["disks"].append({"size" : args.ssd, "type" : "ssd", "fs" : "xfs"})
    if args.hdd:
        data["disks"].append({"size" : args.hdd, "type" : "hdd", "fs": "xfs"})

    return requests.post("http://%s/vms" % args.allocator, json=data)


def _do_delete(args):
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

    create = commands.add_parser("create", help="Create VM")
    create.add_argument("--image", help="Name of base image from which to create VM", required=True)
    create.add_argument("--ram", help="Ram in GBytes", type=int, required=True)
    create.add_argument("--ssd", help="SSD disk in Gbytes", type=int, required=False)
    create.add_argument("--hdd", help="HDD disk in Gbytes", type=int, required=False)
    create.add_argument("--cpus", help="Number of CPU`s to allocate", type=int, required=True)
    create.add_argument("--networks", dest="accumulate", action="store_const", const=sum, default=max, help="Specify networks")
    create.add_argument("networks_all", metavar="N", type=str, nargs="+", help="Networks", default=["bridge"])
    create.add_argument("--gpus", help="Number of GPU`s to allocate", required=False, type=int, default=0)

    create = commands.add_parser("delete", help="Delete VM")
    create.add_argument("--name", help="Name of the VM to delete", required=True)

    create = commands.add_parser("images", help="List images")
    create = commands.add_parser("list", help="List vms")

    create = commands.add_parser('poweroff', help="Poweroff VM")
    create.add_argument('--name', help="Name of the VM to poweoff", required=True)

    create = commands.add_parser('poweron', help="Poweron VM")
    create.add_argument('--name', help="Name of the VM to poweron", required=True)

    create = commands.add_parser('info', help="Get VM information")
    create.add_argument('--name', help="Name of the VM", required=True)

    commands = {"create" : _do_create,
                "delete" : _do_delete,
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
