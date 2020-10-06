import asyncio
import concurrent
import traceback
from asyncio import shield

from aiohttp import web
import logging
# web.View

# from aiohttp import web


class HyperVisor(object):

    def __init__(self, allocator, image_store, webapp):
        self.allocator = allocator
        self.image_store = image_store
        webapp.router.add_routes([web.post('/vms', self.handle_allocate_vm),
                                  web.delete('/vms/{name}', self.handle_destroy_vm),
                                  web.get('/vms', self.handle_list_vms),
                                  web.get('/images', self.handle_list_images),
                                  web.post('/vms/{name}/status', self.handle_vm_update),
                                  web.get('/vms/{name}', self.handle_vm_status),
                                  web.get('/resources', self.handle_resources),
                                  web.post('/fulfill/theoretically', self.check_fulfill),
                                  web.post('/fulfill/now', self.fulfill),
                                  web.delete('/deallocate/{name}', self.handle_destroy_vm),
                                  web.get('/allocations/{allocation_id}', self.handle_get_allocation)])

    def translate_to_vm_params(self, request):
        vm_request_details = list()
        for host, reqs in request['demands'].items():
            vm_args = dict(
                networks=reqs.get('networks', ['bridge']),
                num_cpus=int(reqs.get('cpus', 10)),
                num_gpus=int(reqs.get('gpus', 1)),
                base_image=reqs.get('image', 'ubuntu-compose_v2'),
                base_image_size=reqs.get('size', 150),
                memory_gb=int(reqs.get('ram', 20)),
                disks=reqs.get('disks', None),
                allocation_id=request.get('allocation_id', None),
                requestor=request.get('requestor', None)
            )
            vm_request_details.append(vm_args)
        return vm_request_details

    async def check_fulfill(self, request):
        """request: {"host": {"whatever": "value", "foo": "bar"}"""
        data = await request.json()
        logging.info(f"received a check_fulfill request: {data}")
        vm_requests = self.translate_to_vm_params(data)
        possible = list()
        for vm in vm_requests:
            possible.append(await self.allocator.check_allocate(**vm))

        if all(possible):
            return web.json_response({"status": "Success"}, status=200)
        else:
            return web.json_response({"status": "Unable"}, status=406)

    async def fulfill(self, request):
        """request: demands: {{"host1": {"cpus": "value", "foo": "bar"},
                    "host2": {"cpus": "value", "foo": "bar"}},
                    "allocation_id":"1234-234523-2342-23424"}"""
        data = await request.json()
        vm_requests = self.translate_to_vm_params(data)
        tasks = set()
        for vm_request in vm_requests:
            logging.info(f"allocating vm with args: {vm_request}")
            tasks.add(self.allocator.allocate_vm(**vm_request))

        done, pending = await asyncio.wait(tasks)
        exceptions = set([_task for _task in done if _task.exception() is not None])
        completed = done.difference(exceptions)
        logging.warning(f"completed: {completed}, exceptions: {exceptions}")
        if exceptions:
            destroy_tasks = [self.allocator.destroy_vm(_task.result().name) for _task in completed]
            logging.warning(f"exceptions trying to fulfill. destroy_tasks: {destroy_tasks}")
            await asyncio.gather(*destroy_tasks)
            return web.json_response({'status': 'Failed', 'error': 'error creating'}, status=500)

        return web.json_response(
            {'status': 'Success', 'info': [_task.result().json for _task in completed]}, status=200)

    async def handle_allocate_vm(self, request):
        data = await request.json()

        networks = data['networks']
        num_cpus = int(data.get('num_cpus', 1))
        num_gpus = int(data.get('num_gpus', 0))
        base_image = data['base_image']
        base_image_size = data.get('base_image_size', None)
        memory_gb = int(data['ram'])
        disks = data['disks']
        allocation_id = data.get('allocation_id', None)
        try:
            vm = await self.allocator.allocate_vm(base_image=base_image,
                                       base_image_size=base_image_size,
                                       memory_gb=memory_gb,
                                       networks=networks,
                                       num_gpus=num_gpus,
                                       num_cpus=num_cpus,
                                       disks=disks,
                                       allocation_id=allocation_id)
        except Exception as e:
            logging.exception("Failed to create VM")
            return web.json_response({'status': 'Failed', 'error': str(e)}, status=500)
        else:
            return web.json_response({'status' : 'Success', 'name': vm.name, 'info' : vm.json}, status=200)

    async def handle_destroy_vm(self, request):
        vm_name = request.match_info['name']
        try:
            await shield(self.allocator.destroy_vm(vm_name))
        except KeyError:
            return web.json_response({"error": f'vm {vm_name} doesnt exist'}, status=404)
        except concurrent.futures._base.CancelledError:
            logging.warning("handle_destroy_vm request was cancelled before it completed. "
                            "The vm will still be destroyed but this may point to a bug")
        except Exception as e:
            logging.exception("Failed to destroy VM")
            return web.json_response({'status': 'Failed', 'error': traceback.format_exc(e)}, status=500)
        return web.json_response({'status' : 'Success'}, status=200)

    async def handle_list_vms(self, _):
        vms_info = [vm.json for vm in self.allocator.vms.values()]
        result = []
        for vm_info in vms_info:
            vm = self.allocator.vms.get(vm_info['name'])
            if vm is None:
                continue
            status = await self.allocator.vm_manager.vm_status(vm)
            vm_info.update({"status" : status})
            result.append(vm_info)

        return web.json_response({'vms' : result}, status=200)

    async def handle_list_images(self, _):
        images = await self.image_store.list_images()
        return web.json_response({'images' : images}, status=200)

    async def handle_vm_update(self, request):
        vm_name = request.match_info['name']
        data = await request.json()
        logging.info("Asked to change vm %s status to %s", vm_name, data)
        vm = self.allocator.vms.get(vm_name)
        if vm is None:
            return web.json_response({'error': f'couldnt find vm {vm_name}'}, status=404)

        power_status = data['power']

        async with vm.lock:
            # double check after lock
            if vm_name not in self.allocator.vms:
                return web.json_response({'error': f'couldnt find vm {vm_name} after lock'}, status=404)
            if power_status == "on":
                await self.allocator.vm_manager.start_vm(vm)
            elif power_status == "off":
                await self.allocator.vm_manager.stop_vm(vm)
        return web.json_response({'status' : 'Success'}, status=200)

    async def handle_vm_status(self, request):
        vm_name = request.match_info['name']
        logging.debug("Requested vm info for vm %s", vm_name)
        vm = self.allocator.vms.get(vm_name)
        if vm is None:
            return web.json_response({'error': f'couldnt find vm {vm_name}'}, status=404)
        async with vm.lock:
            # double check after lock
            if vm_name not in self.allocator.vms:
                return web.json_response({'error': f'couldnt find vm {vm_name} after lock'}, status=404)
            info = await self.allocator.vm_manager.info(vm)
        return web.json_response({'info' : info}, status=200)

    async def handle_resources(self, _):
        response = {'gpus' : self.allocator.gpus_list,
                    'macs' : self.allocator.mac_addresses,
                    'sol_used_ports' : self.allocator.sol_used_ports}
        return web.json_response(response, status=200)

    async def handle_get_allocation(self, request):
        allocation_id = request.match_info['allocation_id']
        allocated_vms = [vm.json for vm in self.allocator.vms.values() if vm.allocation_id == allocation_id]
        return web.json_response(
            {'status': 'Success', 'info': allocated_vms}, status=200)
