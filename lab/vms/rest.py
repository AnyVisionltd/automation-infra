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
                                  web.get('/images', self.handle_list_images)])

    async def handle_allocate_vm(self, request):
        data = await request.json()

        networks = data['networks']
        num_cpus = int(data.get('num_cpus', 1))
        num_gpus = int(data.get('num_gpus', 0))
        base_image = data['base_image']
        memory_gb = int(data['ram'])
        try:
            vm = await self.allocator.allocate_vm(base_image=base_image,
                                       memory_gb=memory_gb,
                                       networks=networks,
                                       num_gpus=num_gpus,
                                       num_cpus=num_cpus)
        except:
            logging.exception("Failed to create VM")
            return web.json_response({'status' : 'Failed'}, status=500)
        else:
            return web.json_response({'status' : 'Success', 'name': vm.name}, status=200)

    async def handle_destroy_vm(self, request):
        vm_name = request.match_info['name']
        try:
            await self.allocator.destroy_vm(vm_name)
        except:
            logging.exception("Failed to destroy VM")
            return web.json_response({'status' : 'Failed'}, status=500)
        else:
            return web.json_response({'status' : 'Success'}, status=200)

    async def handle_list_vms(self, _):
        return web.json_response({'vms' : self.allocator.vms}, status=200)

