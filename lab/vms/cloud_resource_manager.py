from aiohttp import web
from python_terraform import *

GCE_PROJECT = "/root/terraform/projects/setup-single-instance-gcp-terraform"


class CloudResourceManager(object):

    def __init__(self):
        webapp = web.Application()
        webapp.router.add_routes([web.post('/provision', self.provision_vm),
                                  web.post('/destroy', self.destroy_vm),
                                  web.get('/vms', self.handle_list_vms),
                                  web.get('/images', self.handle_list_images),
                                  web.post('/vms/{name}/status', self.handle_vm_update),
                                  web.get('/vms/{name}', self.handle_vm_status)])
        web.run_app(webapp)

    async def provision_vm(self, request):
        data = await request.json()

        terraform_vars = {
            "customer_name": data["owner_name"],
            "owner_name": data["owner_name"],
            "environment_type": "automation",
            "region_name": data["region"],
            "instance_type": "n1-standard-8",
            "os_type": data["os_type"],
            "root_block_size": 200,
            "root_block_type": "pd-ssd",
            "storage_data_disk_block_size": data["storage"],
            "storage_data_disk_block_type": "pd-standard",
            "ssd_data_disk_block_size": data["ssd"],
            "ssd_data_disk_block_type": "pd-ssd",
            "gce_accelerator_type": "nvidia-tesla-k80",
            "gce_accelerator_count": 1
        }

        tf = Terraform(working_dir=GCE_PROJECT, variables=terraform_vars)
        tf.plan(no_color=IsFlagged, refresh=False, capture_output=False)
        approve = {"auto_approve": True, "capture_output": False}
        print(tf.plan())
        return_code, stdout, stderr = tf.apply(**approve)
        if return_code != 0:
            logging.exception("Failed to create VM")
            return web.json_response({'status': 'Provision Failed with exit %i' % return_code}, status=500)
        else:
            return web.json_response({'status': 'Success', 'name': data["owner_name"]}, status=200)

    async def destroy_vm(self, request):
        data = await request.json()
        owner_name = data["owner_name"]
        terraform_vars = {
            "prefix": "terraform/%s/automation/%s" % (data["region_name"], owner_name)

        }
        tf = Terraform(working_dir=GCE_PROJECT)
        return_code, stdout, stderr = tf.init(
            backend_config={"prefix": terraform_vars.get("prefix"), "backend": "gcs", "bucket": "tf-state-anyvision"})
        approve = {"auto_approve": True, "capture_output": False}
        tf.destroy(**approve)
        if return_code != 0:
            logging.exception("Failed to destroy VM")
            return web.json_response({'status': 'Failed'}, status=500)
        else:
            return web.json_response({'status': 'Success'}, status=200)

    async def handle_list_vms(self, _):
        vms_info = [vm.json for vm in self.allocator.vms.values()]
        result = []
        for vm_info in vms_info:
            vm = self.allocator.vms.get(vm_info['name'])
            if vm is None:
                continue
            status = await self.allocator.vm_manager.vm_status(vm)
            vm_info.update({"status": status})
            result.append(vm_info)

        return web.json_response({'vms': result}, status=200)

    async def handle_list_images(self, _):
        images = await self.image_store.list_images()
        return web.json_response({'images': images}, status=200)

    async def handle_vm_update(self, request):
        vm_name = request.match_info['name']
        data = await request.json()
        logging.info("Asked to change vm %s status to %s", vm_name, data)
        vm = self.allocator.vms.get(vm_name)
        if vm is None:
            return web.json_response(status=404)

        power_status = data['power']

        async with vm.lock:
            # double check after lock
            if vm_name not in self.allocator.vms:
                return web.json_response(status=404)
            if power_status == "on":
                await self.allocator.vm_manager.start_vm(vm)
            elif power_status == "off":
                await self.allocator.vm_manager.stop_vm(vm)
        return web.json_response({'status': 'Success'}, status=200)

    async def handle_vm_status(self, request):
        vm_name = request.match_info['name']
        logging.debug("Requested vm info for vm %s", vm_name)
        vm = self.allocator.vms.get(vm_name)
        if vm is None:
            return web.json_response(status=404)
        async with vm.lock:
            # double check after lock
            if vm_name not in self.allocator.vms:
                return web.json_response(status=404)
            info = await self.allocator.vm_manager.info(vm)
        return web.json_response({'info': info}, status=200)


c = CloudResourceManager()
