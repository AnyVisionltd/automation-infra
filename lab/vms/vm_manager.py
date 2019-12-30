import concurrent.futures
import logging


class VMManager(object):

    def __init__(self, loop, libvirt_api, image_store):
        self.loop = loop 
        self.libvirt_api = libvirt_api
        self.image_store = image_store
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    async def allocate_vm(self, vm):
        image_path = await self.image_store.clone_qcow(vm['base_image'], vm['name'])
        vm['image'] = image_path
        try:
            await self.loop.run_in_executor(self.thread_pool,
                                                     lambda: self.libvirt_api.define_vm(vm))
            await self.loop.run_in_executor(self.thread_pool,
                                               lambda: self.libvirt_api.start_vm(vm))
        except:
            logging.error("Failed to create VM %s", vm)
            await self.destroy_vm(vm)
            await self.image_store.delete_qcow(vm['image'])
            del vm['image']
            raise
        else:
            return vm

    async def destroy_vm(self, vm):
        await self.loop.run_in_executor(self.thread_pool,
                                        lambda: self.libvirt_api.kill_by_name(vm["name"]))
        await self.image_store.delete_qcow(vm['image'])
        del vm['image']

